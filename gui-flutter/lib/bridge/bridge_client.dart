import 'dart:async';
import 'dart:convert';
import 'dart:io';

enum BridgeStatus { connecting, connected, error }

class BridgeException implements Exception {
  final String message;
  BridgeException(this.message);

  @override
  String toString() => message;
}

class BridgeEvent {
  final int requestId;
  final String method;
  final dynamic data;
  BridgeEvent(this.requestId, this.method, this.data);
}

class BridgeClient {
  Process? _process;
  StreamSubscription<String>? _stdoutSub;
  int _nextId = 1;
  final Map<int, Completer<dynamic>> _pending = {};

  final _statusController = StreamController<BridgeStatus>.broadcast();
  Stream<BridgeStatus> get statusStream => _statusController.stream;

  final _eventController = StreamController<BridgeEvent>.broadcast();
  Stream<BridgeEvent> get eventStream => _eventController.stream;

  BridgeStatus _status = BridgeStatus.connecting;
  BridgeStatus get status => _status;

  String? _lastError;
  String? get lastError => _lastError;

  Future<void> start() async {
    _setStatus(BridgeStatus.connecting);
    try {
      final process = await _startBackend();
      _process = process;
      _stdoutSub = process.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(_handleLine, onError: _handleStreamError);
      process.stderr
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) => _lastError = line);
      unawaited(process.exitCode.then((code) {
        if (code != 0 && _status != BridgeStatus.error) {
          _setStatus(BridgeStatus.error, 'Bridge process exited with code $code');
        }
      }));

      final pong = await call('system.ping', {}).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw BridgeException('Bridge did not respond in time'),
      );
      if (pong['admin'] != true) {
        final hint = Platform.isWindows
            ? 'Bridge is not running with administrator privileges'
            : 'Bridge is not running as root — relaunch this app with sudo';
        _setStatus(BridgeStatus.error, hint);
        return;
      }
      _setStatus(BridgeStatus.connected);
    } catch (e) {
      _setStatus(BridgeStatus.error, e.toString());
    }
  }

  Future<Process> _startBackend() async {
    final exeDir = File(Platform.resolvedExecutable).parent;
    final bundledName = Platform.isWindows ? 'hackmate-bridge.exe' : 'hackmate-bridge';
    final bundled = File('${exeDir.path}/$bundledName');
    if (bundled.existsSync()) {
      return Process.start(bundled.path, [], workingDirectory: exeDir.path);
    }
    final scriptPath = _resolveBridgeScript();
    return _startPython(scriptPath);
  }

  Future<Process> _startPython(String scriptPath) async {
    final candidates = Platform.isWindows ? ['python', 'py'] : ['python3', 'python'];
    Object? lastError;
    for (final exe in candidates) {
      try {
        return await Process.start(
          exe,
          [scriptPath],
          workingDirectory: File(scriptPath).parent.path,
        );
      } catch (e) {
        lastError = e;
      }
    }
    throw BridgeException('Could not find a Python interpreter (tried ${candidates.join(", ")}): $lastError');
  }

  String _resolveBridgeScript() {
    for (final start in [
      File(Platform.resolvedExecutable).parent,
      Directory.current,
    ]) {
      Directory dir = start;
      for (var i = 0; i < 12; i++) {
        final candidate = File('${dir.path}/src/bridge.py');
        if (candidate.existsSync()) return candidate.absolute.path;
        final parent = dir.parent;
        if (parent.path == dir.path) break;
        dir = parent;
      }
    }
    throw BridgeException('Could not locate src/bridge.py relative to the app');
  }

  void _handleStreamError(Object error) {
    _setStatus(BridgeStatus.error, error.toString());
  }

  void _handleLine(String line) {
    if (line.trim().isEmpty) return;
    Map<String, dynamic> message;
    try {
      message = jsonDecode(line) as Map<String, dynamic>;
    } catch (_) {
      return;
    }

    final method = message['method'];
    if (method != null) {
      if (method == 'fatal') {
        _setStatus(BridgeStatus.error, message['data']?.toString() ?? 'Bridge fatal error');
        return;
      }
      final requestId = message['request_id'];
      if (requestId is int) {
        _eventController.add(BridgeEvent(requestId, method as String, message['data']));
      }
      return;
    }

    final id = message['id'];
    if (id is! int) return;
    final completer = _pending.remove(id);
    if (completer == null) return;

    if (message.containsKey('error') && message['error'] != null) {
      completer.completeError(BridgeException(message['error'].toString()));
    } else {
      completer.complete(message['result']);
    }
  }

  Future<dynamic> call(String method, [Map<String, dynamic> params = const {}]) {
    final process = _process;
    if (process == null) {
      return Future.error(BridgeException('Bridge is not running'));
    }
    final id = _nextId++;
    final completer = Completer<dynamic>();
    _pending[id] = completer;
    final request = jsonEncode({'id': id, 'method': method, 'params': params});
    process.stdin.writeln(request);
    return completer.future;
  }

  Future<dynamic> callStreaming(
    String method,
    Map<String, dynamic> params,
    void Function(BridgeEvent event) onEvent,
  ) {
    final process = _process;
    if (process == null) {
      return Future.error(BridgeException('Bridge is not running'));
    }
    final id = _nextId++;
    final completer = Completer<dynamic>();
    _pending[id] = completer;
    final subscription = eventStream.where((e) => e.requestId == id).listen(onEvent);
    final request = jsonEncode({'id': id, 'method': method, 'params': params});
    process.stdin.writeln(request);
    return completer.future.whenComplete(subscription.cancel);
  }

  void _setStatus(BridgeStatus status, [String? error]) {
    _status = status;
    _lastError = error;
    _statusController.add(status);
  }

  void dispose() {
    _stdoutSub?.cancel();
    _process?.kill();
    _statusController.close();
    _eventController.close();
    for (final completer in _pending.values) {
      if (!completer.isCompleted) {
        completer.completeError(BridgeException('Bridge disposed'));
      }
    }
    _pending.clear();
  }
}
