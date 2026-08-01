import 'package:flutter/material.dart';

import '../../bridge/bridge_client.dart';
import 'steps_confirm_install.dart';
import 'steps_hardware.dart';
import 'steps_options.dart';
import 'wizard_state.dart';

String _titleFor(WizardStep step) {
  switch (step) {
    case WizardStep.hardware:
      return 'Hardware Scan';
    case WizardStep.manualHardware:
      return 'Manual Hardware Setup';
    case WizardStep.version:
      return 'Select macOS Version';
    case WizardStep.usbTarget:
      return 'Select USB Target';
    case WizardStep.buildMode:
      return 'Build Mode';
    case WizardStep.wifiKext:
      return 'WiFi Kext Mode';
    case WizardStep.gpuChoice:
      return 'GPU Choice';
    case WizardStep.dgpu:
      return 'Discrete GPU';
    case WizardStep.dualBoot:
      return 'Dual Boot';
    case WizardStep.confirm:
      return 'Confirm & Build';
    case WizardStep.install:
      return 'Building';
    case WizardStep.biosChecklist:
      return 'BIOS Checklist';
  }
}

class BuildEfiFlow extends StatefulWidget {
  final BridgeClient bridge;
  final bool manual;

  const BuildEfiFlow({super.key, required this.bridge, required this.manual});

  @override
  State<BuildEfiFlow> createState() => _BuildEfiFlowState();
}

class _BuildEfiFlowState extends State<BuildEfiFlow> {
  late final WizardState _state;

  @override
  void initState() {
    super.initState();
    _state = WizardState(bridge: widget.bridge, manual: widget.manual);
  }

  @override
  void dispose() {
    _state.dispose();
    super.dispose();
  }

  Widget _buildStep(WizardStep step) {
    switch (step) {
      case WizardStep.hardware:
        return HardwareStep(state: _state);
      case WizardStep.manualHardware:
        return ManualHardwareStep(state: _state);
      case WizardStep.version:
        return VersionStep(state: _state);
      case WizardStep.usbTarget:
        return UsbTargetStep(state: _state);
      case WizardStep.buildMode:
        return BuildModeStep(state: _state);
      case WizardStep.wifiKext:
        return WifiKextStep(state: _state);
      case WizardStep.gpuChoice:
        return GpuChoiceStep(state: _state);
      case WizardStep.dgpu:
        return DgpuStep(state: _state);
      case WizardStep.dualBoot:
        return DualBootStep(state: _state);
      case WizardStep.confirm:
        return ConfirmStep(state: _state);
      case WizardStep.install:
        return InstallStep(state: _state);
      case WizardStep.biosChecklist:
        return BiosChecklistStep(state: _state);
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
          ListenableBuilder(
            listenable: _state,
            builder: (context, _) {
              final canGoBack = _state.backStack.isNotEmpty && !_state.installRunning;
              return Row(
                children: [
                  Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: scheme.secondaryContainer,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Icon(
                      widget.manual ? Icons.handyman_rounded : Icons.construction_rounded,
                      size: 28,
                      color: scheme.onSecondaryContainer,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      _titleFor(_state.step),
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
                    ),
                  ),
                  if (canGoBack)
                    OutlinedButton.icon(
                      onPressed: _state.back,
                      icon: const Icon(Icons.arrow_back_rounded),
                      label: const Text('Back'),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 24),
          Expanded(
            child: ListenableBuilder(
              listenable: _state,
              builder: (context, _) => _buildStep(_state.step),
            ),
          ),
        ],
      ),
    );
  }
}
