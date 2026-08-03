import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';
import '../util/folder_picker.dart';

class RecoveryDownloadScreen extends StatefulWidget {
  final BridgeClient bridge;

  const RecoveryDownloadScreen({super.key, required this.bridge});

  @override
  State<RecoveryDownloadScreen> createState() => _RecoveryDownloadScreenState();
}

class _RecoveryDownloadScreenState extends State<RecoveryDownloadScreen> {
  Future<void>? _loadFuture;
  List<dynamic> _versions = [];
  Map<String, dynamic>? _selectedVersion;
  String? _destFolder;
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
    final result = await widget.bridge.call('recovery.all_versions');
    if (!mounted) return;
    setState(() {
      _versions = result['versions'] as List<dynamic>;
      _selectedVersion = _versions.isNotEmpty ? _versions.first as Map<String, dynamic> : null;
    });
  }

  Future<void> _pickFolder() async {
    try {
      final path = await pickFolder(description: 'Select a folder to save the recovery image to');
      if (path != null && mounted) setState(() => _destFolder = path);
    } on FolderPickerException catch (e) {
      if (!mounted) return;
      setState(() {
        _resultOk = false;
        _resultMessage = e.message;
      });
    }
  }

  Future<void> _runDownload() async {
    final version = _selectedVersion;
    final dest = _destFolder;
    if (version == null || dest == null) return;

    setState(() {
      _running = true;
      _resultMessage = null;
      _log.clear();
    });
    try {
      final result = await widget.bridge.callStreaming(
        'recovery.download',
        {'macos_version': version, 'dest': dest},
        (event) {
          if (!mounted) return;
          final data = event.data as Map<String, dynamic>?;
          setState(() => _log.add(data?['message']?.toString() ?? ''));
        },
      ) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _resultOk = result['ok'] == true;
        _resultMessage = result['ok'] == true
            ? 'Downloaded to ${result['dest']}'
            : (result['message']?.toString() ?? 'Download failed.');
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
                child: Icon(Icons.cloud_download_rounded, size: 28, color: scheme.onSecondaryContainer),
              ),
              const SizedBox(width: 16),
              Text(
                'Download Recovery',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            "Fetches a macOS recoveryOS image straight from Apple, independent of the build "
            "wizard — useful for replacing a corrupt recovery or troubleshooting without "
            "reformatting a USB.",
            style: Theme.of(context).textTheme.bodyMedium,
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
                return SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('macOS version', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      IgnorePointer(
                        ignoring: _running,
                        child: DropdownButtonFormField<String>(
                          initialValue: _selectedVersion?['version'] as String?,
                          decoration: const InputDecoration(border: OutlineInputBorder()),
                          items: [
                            for (final v in _versions)
                              DropdownMenuItem(
                                value: v['version'] as String,
                                child: Text(
                                  '${v['name']}'
                                  '${(v['notes'] as String?)?.isNotEmpty == true ? "  —  ${v['notes']}" : ""}',
                                ),
                              ),
                          ],
                          onChanged: (value) => setState(() {
                            _selectedVersion = _versions.firstWhere((v) => v['version'] == value) as Map<String, dynamic>;
                          }),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text('Save to', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              readOnly: true,
                              controller: TextEditingController(text: _destFolder ?? ''),
                              decoration: const InputDecoration(
                                hintText: 'No folder selected',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          OutlinedButton.icon(
                            onPressed: _running ? null : _pickFolder,
                            icon: const Icon(Icons.folder_open_rounded),
                            label: const Text('Choose folder'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      FilledButton.icon(
                        onPressed: (!_running && _selectedVersion != null && _destFolder != null)
                            ? _runDownload
                            : null,
                        icon: const Icon(Icons.download_rounded),
                        label: const Text('Download'),
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
