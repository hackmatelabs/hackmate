import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';

class RestoreScreen extends StatefulWidget {
  final BridgeClient bridge;

  const RestoreScreen({super.key, required this.bridge});

  @override
  State<RestoreScreen> createState() => _RestoreScreenState();
}

class _RestoreScreenState extends State<RestoreScreen> {
  Future<void>? _loadFuture;
  List<dynamic> _backups = [];
  List<dynamic> _drives = [];
  String? _selectedBackup;
  String? _selectedDevice;
  final _confirmController = TextEditingController();
  bool _running = false;
  String? _resultMessage;
  bool _resultOk = true;
  final List<String> _log = [];

  @override
  void initState() {
    super.initState();
    _loadFuture = _load();
  }

  Future<void> _load() async {
    final backupsResult = await widget.bridge.call('restore.list_backups');
    final drivesResult = await widget.bridge.call('usb.list_drives');
    if (!mounted) return;
    setState(() {
      _backups = backupsResult['backups'] as List<dynamic>;
      _drives = drivesResult['drives'] as List<dynamic>;
      _selectedBackup = _backups.isNotEmpty ? _backups.first['filename'] as String : null;
      _selectedDevice = _drives.isNotEmpty ? _drives.first['device'] as String : null;
    });
  }

  String get _expectedPhrase => 'RESTORE ${_selectedDevice ?? ''}';

  Future<void> _runRestore() async {
    setState(() {
      _running = true;
      _resultMessage = null;
      _log.clear();
    });
    try {
      await widget.bridge.callStreaming(
        'restore.run',
        {
          'device': _selectedDevice,
          'backup_filename': _selectedBackup,
          'confirm_phrase': _confirmController.text,
        },
        (event) {
          if (!mounted) return;
          final data = event.data as Map<String, dynamic>?;
          setState(() => _log.add(data?['message']?.toString() ?? ''));
        },
      );
      if (!mounted) return;
      setState(() {
        _resultOk = true;
        _resultMessage = 'Restore complete.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _resultOk = false;
        _resultMessage = e is BridgeException ? e.message : e.toString();
      });
    } finally {
      if (mounted) setState(() => _running = false);
    }
  }

  @override
  void dispose() {
    _confirmController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: scheme.secondaryContainer,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Icon(Icons.restore_rounded, size: 28, color: scheme.onSecondaryContainer),
              ),
              const SizedBox(width: 16),
              Text(
                'Restore EFI',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Expanded(
            child: FutureBuilder<void>(
              future: _loadFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: Text(snapshot.error.toString(), style: TextStyle(color: scheme.error)),
                  );
                }
                if (_backups.isEmpty) {
                  return const Center(
                    child: Text('No backups found. Backups are created automatically when you build with "Repair EFI".'),
                  );
                }
                if (_drives.isEmpty) {
                  return const Center(child: Text('No USB drives detected. Plug one in and reopen this page.'));
                }
                return SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Select backup', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      IgnorePointer(
                        ignoring: _running,
                        child: RadioGroup<String>(
                          groupValue: _selectedBackup,
                          onChanged: (v) => setState(() => _selectedBackup = v),
                          child: Column(
                            children: [
                              for (final b in _backups)
                                RadioListTile<String>(
                                  value: b['filename'] as String,
                                  title: Text(b['stem'] as String),
                                  subtitle: Text('${b['size_kb']} KB'),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text('Restore to', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      IgnorePointer(
                        ignoring: _running,
                        child: RadioGroup<String>(
                          groupValue: _selectedDevice,
                          onChanged: (v) => setState(() => _selectedDevice = v),
                          child: Column(
                            children: [
                              for (final d in _drives)
                                RadioListTile<String>(
                                  value: d['device'] as String,
                                  title: Text('${d['device']}  ${d['size']}  ${d['label']}'),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: scheme.errorContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.warning_amber_rounded, color: scheme.onErrorContainer),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'This will overwrite the EFI partition on the target USB.',
                                style: TextStyle(color: scheme.onErrorContainer),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text('Type "$_expectedPhrase" to continue:'),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _confirmController,
                        enabled: !_running,
                        decoration: InputDecoration(hintText: _expectedPhrase, border: const OutlineInputBorder()),
                        onChanged: (_) => setState(() {}),
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: (!_running && _confirmController.text == _expectedPhrase) ? _runRestore : null,
                        icon: const Icon(Icons.restore_rounded),
                        label: const Text('Restore'),
                      ),
                      if (_log.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: scheme.surfaceContainerHigh,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [for (final line in _log) Text(line)],
                          ),
                        ),
                      ],
                      if (_resultMessage != null) ...[
                        const SizedBox(height: 16),
                        Text(
                          _resultMessage!,
                          style: TextStyle(color: _resultOk ? Colors.greenAccent : scheme.error),
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
