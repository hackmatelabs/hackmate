import 'package:flutter/material.dart';

import 'wizard_state.dart';

class HardwareStep extends StatefulWidget {
  final WizardState state;

  const HardwareStep({super.key, required this.state});

  @override
  State<HardwareStep> createState() => _HardwareStepState();
}

class _HardwareStepState extends State<HardwareStep> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.state.profile == null && !widget.state.loading) {
        widget.state.runScan();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final state = widget.state;

    if (state.loading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Scanning hardware...'),
          ],
        ),
      );
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(state.error!, style: TextStyle(color: scheme.error)),
            const SizedBox(height: 16),
            FilledButton(onPressed: state.runScan, child: const Text('Retry scan')),
          ],
        ),
      );
    }

    final profile = state.profile;
    if (profile == null) {
      return Center(child: FilledButton(onPressed: state.runScan, child: const Text('Scan hardware')));
    }

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Detected hardware', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _row('CPU', '${profile['cpu_name']} (gen ${profile['cpu_generation']}, ${profile['platform']})'),
                  _row('GPU', profile['gpu_name']?.toString() ?? ''),
                  _row('Audio', profile['audio_codec']?.toString() ?? ''),
                  _row('Ethernet', profile['ethernet_chipset']?.toString() ?? ''),
                  _row('WiFi', profile['wifi_chipset']?.toString() ?? '(none)'),
                  _row('SMBIOS target', profile['smbios_model']?.toString() ?? ''),
                ],
              ),
            ),
          ),
          if (state.profileWarnings.isNotEmpty) ...[
            const SizedBox(height: 16),
            for (final w in state.profileWarnings)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.warning_amber_rounded, size: 18, color: Colors.amber),
                    const SizedBox(width: 8),
                    Expanded(child: Text(w)),
                  ],
                ),
              ),
          ],
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () => state.goTo(WizardStep.version),
            icon: const Icon(Icons.arrow_forward_rounded),
            label: const Text('Continue'),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          SizedBox(width: 100, child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600))),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

class ManualHardwareStep extends StatefulWidget {
  final WizardState state;

  const ManualHardwareStep({super.key, required this.state});

  @override
  State<ManualHardwareStep> createState() => _ManualHardwareStepState();
}

class _ManualHardwareStepState extends State<ManualHardwareStep> {
  String? _cpuKey;
  String _gpuKey = '';
  String _ethKey = '';
  String _wifiKey = '';
  bool _isLaptop = true;
  bool _nvme = true;
  bool _thunderbolt = false;
  final _coresController = TextEditingController(text: '4');
  final _audioController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.state.loadManualOptions();
    });
  }

  @override
  void dispose() {
    _coresController.dispose();
    _audioController.dispose();
    super.dispose();
  }

  List<List<dynamic>> _filterCpu(List<dynamic> all, bool Function(String) predicate) {
    return all.cast<List<dynamic>>().where((o) => predicate(o[0] as String)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final state = widget.state;
    final scheme = Theme.of(context).colorScheme;

    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        if (state.loading || state.manualOptions == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (state.error != null) {
          return Center(child: Text(state.error!, style: TextStyle(color: scheme.error)));
        }

        final opts = state.manualOptions!;
        final cpuOptions = opts['cpu_options'] as List<dynamic>;
        final gpuOptions = (opts['gpu_options'] as List).cast<List<dynamic>>();
        final ethOptions = (opts['ethernet_options'] as List).cast<List<dynamic>>();
        final wifiOptions = (opts['wifi_options'] as List).cast<List<dynamic>>();
        _cpuKey ??= cpuOptions.length > 6 ? cpuOptions[6][0] as String : (cpuOptions.isNotEmpty ? cpuOptions[0][0] as String : null);

        bool endsWithAny(String k, List<String> suffixes) => suffixes.any((s) => k.endsWith(s));

        final intelDesktop = _filterCpu(
          cpuOptions,
          (k) => k.startsWith('intel-') && !k.endsWith('m') && !endsWithAny(k, ['kr', 'wl', 'cl', 'cm', 'il', 'tl']),
        );
        final intelLaptop = _filterCpu(
          cpuOptions,
          (k) => k.startsWith('intel-') && (k.endsWith('m') || endsWithAny(k, ['kr', 'wl', 'cl', 'cm', 'il', 'tl'])),
        );
        final amdDesktop = _filterCpu(cpuOptions, (k) => k.startsWith('amd-') && k.endsWith('d'));
        final amdTr = _filterCpu(cpuOptions, (k) => k.startsWith('amd-tr'));
        final amdLaptop = _filterCpu(cpuOptions, (k) => k.startsWith('amd-') && k.endsWith('m'));

        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _cpuRadioSection('CPU — Intel Desktop', intelDesktop),
              _cpuRadioSection('CPU — Intel Laptop', intelLaptop),
              _cpuRadioSection('CPU — AMD Desktop', amdDesktop),
              _cpuRadioSection('CPU — AMD Threadripper', amdTr),
              _cpuRadioSection('CPU — AMD Laptop / APU', amdLaptop),
              const SizedBox(height: 16),
              Text('Platform', style: Theme.of(context).textTheme.titleMedium),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(_isLaptop ? 'Laptop' : 'Desktop'),
                value: _isLaptop,
                onChanged: (v) => setState(() => _isLaptop = v),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Text('Core count: '),
                  SizedBox(
                    width: 80,
                    child: TextField(
                      controller: _coresController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(isDense: true, border: OutlineInputBorder()),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              _labeledRadioGroup('GPU', gpuOptions, _gpuKey, (v) => setState(() => _gpuKey = v ?? '')),
              const SizedBox(height: 16),
              Text('Audio Codec', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              SizedBox(
                width: 200,
                child: TextField(
                  controller: _audioController,
                  decoration: const InputDecoration(hintText: 'ALC256', border: OutlineInputBorder(), isDense: true),
                ),
              ),
              const SizedBox(height: 16),
              _labeledRadioGroup('Ethernet', ethOptions, _ethKey, (v) => setState(() => _ethKey = v ?? '')),
              const SizedBox(height: 16),
              _labeledRadioGroup('WiFi', wifiOptions, _wifiKey, (v) => setState(() => _wifiKey = v ?? '')),
              const SizedBox(height: 16),
              Text('Other', style: Theme.of(context).textTheme.titleMedium),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('NVMe drive'),
                value: _nvme,
                onChanged: (v) => setState(() => _nvme = v),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Thunderbolt'),
                value: _thunderbolt,
                onChanged: (v) => setState(() => _thunderbolt = v),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _cpuKey == null
                    ? null
                    : () => state.submitManualProfile(
                          cpuKey: _cpuKey!,
                          gpuKey: _gpuKey,
                          ethKey: _ethKey,
                          wifiKey: _wifiKey,
                          isLaptop: _isLaptop,
                          cores: int.tryParse(_coresController.text) ?? 4,
                          audioCodec: _audioController.text,
                          nvmePresent: _nvme,
                          hasThunderbolt: _thunderbolt,
                        ),
                icon: const Icon(Icons.arrow_forward_rounded),
                label: const Text('Continue'),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _cpuRadioSection(String heading, List<List<dynamic>> options) {
    if (options.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(heading, style: Theme.of(context).textTheme.titleMedium),
          RadioGroup<String>(
            groupValue: _cpuKey,
            onChanged: (v) => setState(() => _cpuKey = v),
            child: Column(
              children: [
                for (final o in options)
                  RadioListTile<String>(
                    dense: true,
                    value: o[0] as String,
                    title: Text(o[1] as String),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _labeledRadioGroup(
    String heading,
    List<List<dynamic>> options,
    String groupValue,
    ValueChanged<String?> onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(heading, style: Theme.of(context).textTheme.titleMedium),
        RadioGroup<String>(
          groupValue: groupValue,
          onChanged: onChanged,
          child: Column(
            children: [
              for (final o in options)
                RadioListTile<String>(
                  dense: true,
                  value: o[0] as String,
                  title: Text(o[1] as String),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
