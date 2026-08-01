import 'package:flutter/material.dart';

import 'wizard_state.dart';

class ConfirmStep extends StatefulWidget {
  final WizardState state;

  const ConfirmStep({super.key, required this.state});

  @override
  State<ConfirmStep> createState() => _ConfirmStepState();
}

class _ConfirmStepState extends State<ConfirmStep> {
  final _confirmController = TextEditingController();

  @override
  void dispose() {
    _confirmController.dispose();
    super.dispose();
  }

  (String, String) _actionAndWarning() {
    final state = widget.state;
    if (state.repair) {
      return ('Repair EFI on ${state.device}', 'This will update OpenCore, kexts, and config on the existing USB.');
    }
    if (state.skipFormat) {
      return (
        'WRITE TO (no format) ${state.device}',
        'USB must already be FAT32 formatted. No data will be erased.',
      );
    }
    return ('FORMAT AND WRITE TO ${state.device}', 'ALL DATA ON THIS DRIVE WILL BE PERMANENTLY ERASED.');
  }

  @override
  Widget build(BuildContext context) {
    final state = widget.state;
    final scheme = Theme.of(context).colorScheme;
    final (action, warning) = _actionAndWarning();
    final matches = _confirmController.text == state.expectedConfirmPhrase;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Confirm', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          Text(action, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text('macOS: ${state.macosVersion?['name'] ?? 'unknown'}'),
          if (state.dualBoot.isNotEmpty) Text('Dual boot: ${state.dualBoot}'),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: scheme.errorContainer, borderRadius: BorderRadius.circular(12)),
            child: Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: scheme.onErrorContainer),
                const SizedBox(width: 12),
                Expanded(child: Text(warning, style: TextStyle(color: scheme.onErrorContainer))),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('To continue, type: ${state.expectedConfirmPhrase}'),
          const SizedBox(height: 8),
          TextField(
            controller: _confirmController,
            decoration: InputDecoration(hintText: state.expectedConfirmPhrase, border: const OutlineInputBorder()),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: matches ? () => state.runBuild(_confirmController.text) : null,
            icon: const Icon(Icons.play_arrow_rounded),
            label: const Text('Proceed'),
          ),
        ],
      ),
    );
  }
}

class InstallStep extends StatelessWidget {
  final WizardState state;

  const InstallStep({super.key, required this.state});

  Color _levelColor(ColorScheme scheme, String level) {
    switch (level) {
      case 'error':
      case 'critical':
        return scheme.error;
      case 'warn':
      case 'warning':
        return Colors.amber;
      case 'ok':
        return Colors.greenAccent;
      case 'header':
        return scheme.primary;
      default:
        return scheme.onSurfaceVariant;
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              state.repair ? 'Repairing EFI → ${state.device}' : 'Building EFI → ${state.device}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(state.installMessage),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(value: state.installPct / 100, minHeight: 8),
            ),
            const SizedBox(height: 16),
            if (state.installRunning)
              Container(
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(color: scheme.errorContainer, borderRadius: BorderRadius.circular(12)),
                child: Row(
                  children: [
                    Icon(Icons.info_outline_rounded, color: scheme.onErrorContainer),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        "In progress — don't close this window or unplug the drive.",
                        style: TextStyle(color: scheme.onErrorContainer),
                      ),
                    ),
                  ],
                ),
              ),
            Expanded(
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: scheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(12)),
                child: ListView.builder(
                  itemCount: state.installLog.length,
                  itemBuilder: (context, i) {
                    final entry = state.installLog[i];
                    return Text(
                      entry['message'] ?? '',
                      style: TextStyle(color: _levelColor(scheme, entry['level'] ?? 'info'), fontFamily: 'monospace'),
                    );
                  },
                ),
              ),
            ),
            if (state.installDone) ...[
              const SizedBox(height: 16),
              Text(
                state.installOk ? 'Done.' : 'Failed: ${state.installError}',
                style: TextStyle(color: state.installOk ? Colors.greenAccent : scheme.error),
              ),
            ],
          ],
        );
      },
    );
  }
}

class BiosChecklistStep extends StatelessWidget {
  final WizardState state;

  const BiosChecklistStep({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final isAmd = state.profile?['cpu_vendor'] == 'amd';
    final isNvidia = state.profile?['dgpu_vendor'] == 'nvidia' || state.profile?['gpu_vendor'] == 'nvidia';

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Before you boot: BIOS checklist', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          const _ChecklistItem('Disable Secure Boot'),
          const _ChecklistItem('Disable Fast Boot / Fast Startup'),
          const _ChecklistItem('Disable CSM / enable UEFI-only boot'),
          const _ChecklistItem('Disable VT-d (or leave on if using DisableIoMapper quirk)'),
          const _ChecklistItem('Set SATA mode to AHCI'),
          if (isAmd) const _ChecklistItem('Enable "Above 4G Decoding"'),
          if (isNvidia) const _ChecklistItem('Disable the Nvidia GPU in BIOS, or set boot GPU to iGPU'),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: state.restart,
            child: const Text('Got it'),
          ),
        ],
      ),
    );
  }
}

class _ChecklistItem extends StatelessWidget {
  final String text;

  const _ChecklistItem(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_box_outline_blank_rounded, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
