import 'package:flutter/material.dart';

import '../../util/folder_picker.dart';
import 'wizard_state.dart';

class VersionStep extends StatefulWidget {
  final WizardState state;

  const VersionStep({super.key, required this.state});

  @override
  State<VersionStep> createState() => _VersionStepState();
}

class _VersionStepState extends State<VersionStep> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.state.versions.isEmpty && !widget.state.loading) {
        widget.state.loadVersions();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = widget.state;
    final scheme = Theme.of(context).colorScheme;

    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        if (state.loading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (state.error != null) {
          return Center(child: Text(state.error!, style: TextStyle(color: scheme.error)));
        }
        if (state.versions.isEmpty) {
          return const Center(
            child: Text('No compatible macOS versions found for this hardware.'),
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${state.versions.length} versions compatible with your hardware',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Expanded(
              child: ListView.separated(
                itemCount: state.versions.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (context, i) {
                  final v = state.versions[i] as Map<String, dynamic>;
                  return Card(
                    child: ListTile(
                      title: Text(v['name'] as String),
                      subtitle: (v['notes'] as String?)?.isNotEmpty == true ? Text(v['notes'] as String) : null,
                      onTap: () => state.selectVersion(v),
                    ),
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

class UsbTargetStep extends StatefulWidget {
  final WizardState state;

  const UsbTargetStep({super.key, required this.state});

  @override
  State<UsbTargetStep> createState() => _UsbTargetStepState();
}

class _UsbTargetStepState extends State<UsbTargetStep> {
  bool _noUsbMode = false;
  final _outputPathController = TextEditingController();
  bool _browsing = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.state.drives.isEmpty && !widget.state.loading) {
        widget.state.loadDrives();
      }
    });
  }

  @override
  void dispose() {
    _outputPathController.dispose();
    super.dispose();
  }

  Future<void> _browse() async {
    setState(() => _browsing = true);
    try {
      final path = await pickFolder(description: 'Select a folder to write the EFI to');
      if (path != null) setState(() => _outputPathController.text = path);
    } finally {
      if (mounted) setState(() => _browsing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = widget.state;

    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        if (_noUsbMode) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('No USB — write EFI to a folder', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _outputPathController,
                      decoration: const InputDecoration(labelText: 'Output folder', border: OutlineInputBorder()),
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton(onPressed: _browsing ? null : _browse, child: const Text('Browse…')),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  FilledButton(
                    onPressed: _outputPathController.text.trim().isEmpty
                        ? null
                        : () => state.selectLocalOutput(_outputPathController.text.trim()),
                    child: const Text('Continue'),
                  ),
                  const SizedBox(width: 8),
                  TextButton(onPressed: () => setState(() => _noUsbMode = false), child: const Text('Back to USB list')),
                ],
              ),
            ],
          );
        }

        if (state.loading) {
          return const Center(child: CircularProgressIndicator());
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Select a USB drive', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            if (state.drives.isEmpty)
              const Text('No USB drives detected.')
            else
              Expanded(
                child: ListView.separated(
                  itemCount: state.drives.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, i) {
                    final d = state.drives[i] as Map<String, dynamic>;
                    return Card(
                      child: ListTile(
                        leading: const Icon(Icons.usb_rounded),
                        title: Text('${d['device']}  ${d['size']}'),
                        subtitle: Text((d['label'] as String?)?.isNotEmpty == true ? d['label'] as String : 'No label'),
                        onTap: () => state.selectUsbDevice(d['device'] as String),
                      ),
                    );
                  },
                ),
              ),
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: () => setState(() => _noUsbMode = true),
              icon: const Icon(Icons.folder_outlined),
              label: const Text("Don't have a USB — write to a folder instead"),
            ),
          ],
        );
      },
    );
  }
}

class BuildModeStep extends StatelessWidget {
  final WizardState state;

  const BuildModeStep({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('How should ${state.device} be prepared?', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: const Icon(Icons.restart_alt_rounded),
            title: const Text('Full Build'),
            subtitle: const Text('Format the drive as FAT32 and write everything fresh.'),
            onTap: () => state.selectBuildMode(false, false),
          ),
        ),
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            leading: const Icon(Icons.check_circle_outline_rounded),
            title: const Text('Already Formatted'),
            subtitle: const Text('Skip formatting — drive is already FAT32.'),
            onTap: () => state.selectBuildMode(false, true),
          ),
        ),
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            leading: const Icon(Icons.build_rounded),
            title: const Text('Repair EFI'),
            subtitle: const Text('Update OpenCore, kexts, and config on an existing EFI (backs up first).'),
            onTap: () => state.selectBuildMode(true, false),
          ),
        ),
      ],
    );
  }
}

class WifiKextStep extends StatelessWidget {
  final WizardState state;

  const WifiKextStep({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final isIntel = state.profile?['wifi_chipset'] == 'intel';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('WiFi kext mode', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            title: const Text('Standard itlwm + HeliPort'),
            subtitle: const Text('Works for Intel and most other chipsets.'),
            onTap: () => state.selectWifiKextMode('itlwm'),
          ),
        ),
        if (isIntel) ...[
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              title: const Text('AirportItlwm'),
              subtitle: const Text('Native-feeling WiFi menu, Intel only.'),
              onTap: () => state.selectWifiKextMode('AirportItlwm'),
            ),
          ),
        ],
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            title: const Text('Disable onboard WiFi/BT'),
            subtitle: const Text('Use a supported USB/PCIe WiFi adapter instead.'),
            onTap: () => state.selectWifiKextMode('none'),
          ),
        ),
      ],
    );
  }
}

class GpuChoiceStep extends StatelessWidget {
  final WizardState state;

  const GpuChoiceStep({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Discrete GPU detected', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Text('${state.profile?['dgpu_name'] ?? state.profile?['gpu_name'] ?? 'Unknown GPU'}'),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            title: const Text('This GPU works fine under macOS'),
            subtitle: const Text('Keep it enabled.'),
            onTap: state.selectSupportedGpu,
          ),
        ),
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            title: const Text('This GPU is unsupported (most Nvidia / newer AMD)'),
            subtitle: const Text("I'll decide whether to disable it next."),
            onTap: state.selectUnsupportedGpu,
          ),
        ),
      ],
    );
  }
}

class DgpuStep extends StatelessWidget {
  final WizardState state;

  const DgpuStep({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Disable the discrete GPU?', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        const Text('Recommended for unsupported GPUs to avoid boot issues and improve battery life.'),
        const SizedBox(height: 16),
        Row(
          children: [
            FilledButton(onPressed: () => state.selectDgpuChoice(true), child: const Text('Yes, disable it')),
            const SizedBox(width: 8),
            OutlinedButton(onPressed: () => state.selectDgpuChoice(false), child: const Text('No, keep it enabled')),
          ],
        ),
      ],
    );
  }
}

class DualBootStep extends StatelessWidget {
  final WizardState state;

  const DualBootStep({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Dual boot?', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 16),
        Card(child: ListTile(title: const Text('No other OS'), onTap: () => state.selectDualBoot(''))),
        const SizedBox(height: 8),
        Card(child: ListTile(title: const Text('Windows'), onTap: () => state.selectDualBoot('windows'))),
        const SizedBox(height: 8),
        Card(child: ListTile(title: const Text('Linux'), onTap: () => state.selectDualBoot('linux'))),
        const SizedBox(height: 8),
        Card(child: ListTile(title: const Text('Windows and Linux'), onTap: () => state.selectDualBoot('both'))),
      ],
    );
  }
}
