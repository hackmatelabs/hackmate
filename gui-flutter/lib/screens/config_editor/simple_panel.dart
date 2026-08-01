import 'package:flutter/material.dart';

import 'config_editor_state.dart';

class SimplePanel extends StatelessWidget {
  final ConfigEditorState state;

  const SimplePanel({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Boot arg presets', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final name in state.bootArgPresets.keys)
                    OutlinedButton(onPressed: () => state.applyPreset(name), child: Text(name)),
                ],
              ),
              const SizedBox(height: 16),
              Text('Boot args', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final entry in state.bootArgs.entries)
                    InputChip(
                      label: Text(entry.value == true ? entry.key : '${entry.key}=${entry.value}'),
                      onDeleted: () => state.removeBootArg(entry.key),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              _AddBootArgRow(state: state),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: state.audioCodecController,
                      decoration: const InputDecoration(labelText: 'Audio codec (e.g. ALC295)', border: OutlineInputBorder()),
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton(onPressed: state.suggestAudioLayouts, child: const Text('Suggest')),
                ],
              ),
              if (state.audioLayoutSuggestions.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 8,
                    children: [
                      for (final s in state.audioLayoutSuggestions)
                        ActionChip(
                          label: Text('alcid=${s[0]} (${s[1]})'),
                          onPressed: () => state.applyAudioLayout(s[0] as int),
                        ),
                    ],
                  ),
                ),
              const SizedBox(height: 24),
              Text('OpenCore', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(child: Text('Timeout (seconds)')),
                  SizedBox(
                    width: 100,
                    child: TextFormField(
                      initialValue: state.timeout.toString(),
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
                      onChanged: (v) => state.timeout = int.tryParse(v) ?? state.timeout,
                    ),
                  ),
                ],
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('OpenCore file logging'),
                value: state.ocLogging,
                onChanged: state.setOcLogging,
              ),
              const SizedBox(height: 16),
              Text('Security', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('SIP enabled'),
                value: state.sipEnabled,
                onChanged: state.setSipEnabled,
              ),
              TextField(
                controller: state.secureBootModelController,
                decoration: const InputDecoration(labelText: 'SecureBootModel', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              Text('System', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              TextField(
                controller: state.smbiosModelController,
                decoration: const InputDecoration(labelText: 'SMBIOS model', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              Text('Discrete GPU', style: Theme.of(context).textTheme.titleMedium),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Disable external GPU'),
                value: state.dgpuDisabled,
                onChanged: state.setDgpuDisabled,
              ),
              const SizedBox(height: 16),
              Text('iGPU framebuffer', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text('Current platform-id: ${state.igpuPlatformId.isEmpty ? '(none)' : state.igpuPlatformId}',
                  style: TextStyle(color: scheme.onSurfaceVariant)),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: state.gpuDeviceIdController,
                      decoration: const InputDecoration(labelText: 'GPU device id (e.g. 5916)', border: OutlineInputBorder()),
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton(onPressed: state.suggestFramebuffers, child: const Text('Suggest')),
                ],
              ),
              if (state.framebufferSuggestions.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 8,
                    children: [
                      for (final s in state.framebufferSuggestions)
                        ActionChip(
                          label: Text('${s[1]}'),
                          onPressed: () => state.applyIgpuHex(s[0] as String),
                        ),
                    ],
                  ),
                ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: state.igpuHexController,
                      decoration: const InputDecoration(labelText: 'Manual platform-id (hex)', border: OutlineInputBorder()),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: () => state.applyIgpuHex(state.igpuHexController.text),
                    child: const Text('Apply'),
                  ),
                ],
              ),
              const SizedBox(height: 32),
            ],
          ),
        );
      },
    );
  }
}

class _AddBootArgRow extends StatefulWidget {
  final ConfigEditorState state;

  const _AddBootArgRow({required this.state});

  @override
  State<_AddBootArgRow> createState() => _AddBootArgRowState();
}

class _AddBootArgRowState extends State<_AddBootArgRow> {
  final _keyController = TextEditingController();
  final _valueController = TextEditingController();

  @override
  void dispose() {
    _keyController.dispose();
    _valueController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          flex: 2,
          child: TextField(
            controller: _keyController,
            decoration: const InputDecoration(labelText: 'flag (e.g. -v)', border: OutlineInputBorder(), isDense: true),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          flex: 2,
          child: TextField(
            controller: _valueController,
            decoration: const InputDecoration(labelText: 'value (optional)', border: OutlineInputBorder(), isDense: true),
          ),
        ),
        const SizedBox(width: 8),
        IconButton(
          icon: const Icon(Icons.add_circle_rounded),
          onPressed: () {
            widget.state.addBootArg(_keyController.text, _valueController.text);
            _keyController.clear();
            _valueController.clear();
          },
        ),
      ],
    );
  }
}
