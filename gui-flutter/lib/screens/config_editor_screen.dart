import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';
import 'config_editor/advanced_panel.dart';
import 'config_editor/config_editor_state.dart';
import 'config_editor/simple_panel.dart';

class ConfigEditorScreen extends StatefulWidget {
  final BridgeClient bridge;

  const ConfigEditorScreen({super.key, required this.bridge});

  @override
  State<ConfigEditorScreen> createState() => _ConfigEditorScreenState();
}

class _ConfigEditorScreenState extends State<ConfigEditorScreen> {
  Future<List<String>>? _findFuture;
  String? _openPath;

  @override
  void initState() {
    super.initState();
    _findFuture = _findConfigs();
  }

  Future<List<String>> _findConfigs() async {
    final r = await widget.bridge.call('config_editor.find_configs');
    return (r['paths'] as List).cast<String>();
  }

  void _open(String path) => setState(() => _openPath = path);

  void _closeEditor() => setState(() => _openPath = null);

  @override
  Widget build(BuildContext context) {
    final path = _openPath;
    if (path != null) {
      return _ConfigEditPane(
        key: ValueKey(path),
        bridge: widget.bridge,
        path: path,
        onBack: _closeEditor,
      );
    }

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
                child: Icon(Icons.edit_note_rounded, size: 28, color: scheme.onSecondaryContainer),
              ),
              const SizedBox(width: 16),
              Text(
                'Edit Config',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text('Select a config.plist to edit:'),
          const SizedBox(height: 16),
          Expanded(
            child: FutureBuilder<List<String>>(
              future: _findFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text('${snapshot.error}', style: TextStyle(color: scheme.error)));
                }
                final paths = snapshot.data!;
                if (paths.isEmpty) {
                  return const Center(child: Text('No config.plist found on any mounted USB. Mount your USB first.'));
                }
                return ListView.separated(
                  itemCount: paths.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, i) => Card(
                    child: ListTile(
                      leading: const Icon(Icons.description_outlined),
                      title: Text(paths[i]),
                      onTap: () => _open(paths[i]),
                    ),
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

class _ConfigEditPane extends StatefulWidget {
  final BridgeClient bridge;
  final String path;
  final VoidCallback onBack;

  const _ConfigEditPane({super.key, required this.bridge, required this.path, required this.onBack});

  @override
  State<_ConfigEditPane> createState() => _ConfigEditPaneState();
}

class _ConfigEditPaneState extends State<_ConfigEditPane> {
  late final ConfigEditorState _state;

  @override
  void initState() {
    super.initState();
    _state = ConfigEditorState(bridge: widget.bridge, path: widget.path);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _state.load();
    });
  }

  @override
  void dispose() {
    _state.close();
    _state.dispose();
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
              IconButton(icon: const Icon(Icons.arrow_back_rounded), onPressed: widget.onBack),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  widget.path,
                  style: Theme.of(context).textTheme.titleMedium,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListenableBuilder(
              listenable: _state,
              builder: (context, _) {
                if (_state.loading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (_state.error != null) {
                  return Center(child: Text(_state.error!, style: TextStyle(color: scheme.error)));
                }
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        SegmentedButton<ConfigEditorTab>(
                          segments: const [
                            ButtonSegment(value: ConfigEditorTab.simple, label: Text('Simple')),
                            ButtonSegment(value: ConfigEditorTab.advanced, label: Text('Advanced')),
                          ],
                          selected: {_state.tab},
                          onSelectionChanged: (s) => _state.setTab(s.first),
                        ),
                        const Spacer(),
                        if (_state.saveMessage != null)
                          Padding(
                            padding: const EdgeInsets.only(right: 12),
                            child: Text(
                              _state.saveMessage!,
                              style: TextStyle(color: _state.saveOk ? Colors.greenAccent : scheme.error),
                            ),
                          ),
                        FilledButton.icon(
                          onPressed: _state.saving ? null : () => _state.save(),
                          icon: const Icon(Icons.save_rounded),
                          label: const Text('Save'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: _state.tab == ConfigEditorTab.simple
                          ? SimplePanel(state: _state)
                          : AdvancedPanel(state: _state),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
