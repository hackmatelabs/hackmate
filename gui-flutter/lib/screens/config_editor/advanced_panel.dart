import 'package:flutter/material.dart';

import 'config_editor_state.dart';

class AdvancedPanel extends StatelessWidget {
  final ConfigEditorState state;

  const AdvancedPanel({super.key, required this.state});

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
              Text('Kexts', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  color: scheme.surfaceContainerHigh,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    for (final k in state.kexts)
                      SwitchListTile(
                        dense: true,
                        title: Text(k[0] as String),
                        value: k[1] as bool,
                        onChanged: (v) => state.toggleKext(k[0] as String, v),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Text('ACPI (SSDTs)', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  color: scheme.surfaceContainerHigh,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    for (final a in state.acpi)
                      SwitchListTile(
                        dense: true,
                        title: Text(a[0] as String),
                        value: a[1] as bool,
                        onChanged: (v) => state.toggleAcpi(a[0] as String, v),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Text('Serial / MLB / UUID / ROM', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              TextField(
                controller: state.serialController,
                decoration: const InputDecoration(labelText: 'SystemSerialNumber', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: state.mlbController,
                decoration: const InputDecoration(labelText: 'MLB', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: state.uuidController,
                decoration: const InputDecoration(labelText: 'SystemUUID', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: state.romController,
                decoration: const InputDecoration(labelText: 'ROM (hex)', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 8),
              FilledButton(onPressed: state.applySerialInfo, child: const Text('Apply Serial Info')),
              const SizedBox(height: 24),
              Text('Raw value editor', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              TextField(
                controller: state.rawPathController,
                decoration: const InputDecoration(
                  labelText: 'Dot path (e.g. Misc.Debug.Target)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: state.rawValueController,
                      decoration: const InputDecoration(labelText: 'Value', border: OutlineInputBorder()),
                    ),
                  ),
                  const SizedBox(width: 8),
                  DropdownMenu<String>(
                    initialSelection: state.rawType,
                    dropdownMenuEntries: const [
                      DropdownMenuEntry(value: 'string', label: 'string'),
                      DropdownMenuEntry(value: 'bool', label: 'bool'),
                      DropdownMenuEntry(value: 'int', label: 'int'),
                      DropdownMenuEntry(value: 'data', label: 'data'),
                    ],
                    onSelected: (v) {
                      if (v != null) state.rawType = v;
                    },
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  OutlinedButton(onPressed: state.getRawValue, child: const Text('Get')),
                  const SizedBox(width: 8),
                  FilledButton(onPressed: state.setRawValue, child: const Text('Set')),
                ],
              ),
              if (state.changeLog.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [for (final line in state.changeLog.reversed) Text(line)],
                  ),
                ),
              ],
              const SizedBox(height: 32),
            ],
          ),
        );
      },
    );
  }
}
