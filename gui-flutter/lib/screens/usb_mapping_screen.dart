import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';
import '../util/folder_picker.dart';

class UsbMappingScreen extends StatefulWidget {
  final BridgeClient bridge;

  const UsbMappingScreen({super.key, required this.bridge});

  @override
  State<UsbMappingScreen> createState() => _UsbMappingScreenState();
}

class _UsbMappingScreenState extends State<UsbMappingScreen> {
  Future<void>? _loadFuture;
  List<dynamic> _drives = [];
  String? _selectedDevice;
  final _kextPathController = TextEditingController();
  bool _browsing = false;
  bool _applying = false;
  final List<String> _log = [];
  String? _resultMessage;
  bool _resultOk = true;

  @override
  void initState() {
    super.initState();
    _loadFuture = _load();
  }

  Future<void> _load() async {
    final drivesResult = await widget.bridge.call('usb.list_drives');
    if (!mounted) return;
    setState(() {
      _drives = drivesResult['drives'] as List<dynamic>;
      _selectedDevice = _drives.isNotEmpty ? _drives.first['device'] as String : null;
    });
  }

  Future<void> _browse() async {
    setState(() => _browsing = true);
    try {
      final path = await pickFolder(description: 'Select the UTBMap.kext folder you exported from USBToolBox');
      if (path != null && mounted) {
        setState(() => _kextPathController.text = path);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not open folder picker: $e')));
    } finally {
      if (mounted) setState(() => _browsing = false);
    }
  }

  Future<void> _apply() async {
    setState(() {
      _applying = true;
      _resultMessage = null;
      _log.clear();
    });
    try {
      await widget.bridge.callStreaming(
        'usb_mapping.apply',
        {'device': _selectedDevice, 'utbmap_kext_path': _kextPathController.text.trim()},
        (event) {
          if (!mounted) return;
          final data = event.data as Map<String, dynamic>?;
          setState(() => _log.add(data?['message']?.toString() ?? ''));
        },
      );
      if (!mounted) return;
      setState(() {
        _resultOk = true;
        _resultMessage = 'UTBMap.kext applied — reboot to take effect.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _resultOk = false;
        _resultMessage = e is BridgeException ? e.message : e.toString();
      });
    } finally {
      if (mounted) setState(() => _applying = false);
    }
  }

  @override
  void dispose() {
    _kextPathController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final busy = _applying || _browsing;

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
                child: Icon(Icons.usb_rounded, size: 28, color: scheme.onSecondaryContainer),
              ),
              const SizedBox(width: 16),
              Text(
                'USB Port Mapping (Post-Install)',
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
                return SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('1. Boot into macOS, then run USBToolBox from your USB:'),
                      const Padding(
                        padding: EdgeInsets.only(left: 16, top: 4),
                        child: Text('EFI/HackMate-Extras/  →  map your ports  →  Export'),
                      ),
                      const SizedBox(height: 16),
                      const Text('2. Select the drive with your OpenCore EFI:'),
                      const SizedBox(height: 8),
                      if (_drives.isEmpty)
                        const Text('No USB drives detected.')
                      else
                        IgnorePointer(
                          ignoring: busy,
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
                      const Text('3. Path to your generated UTBMap.kext:'),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _kextPathController,
                              enabled: !busy,
                              decoration: const InputDecoration(
                                hintText: r'e.g. C:\Users\you\Desktop\UTBMap.kext',
                                border: OutlineInputBorder(),
                              ),
                              onChanged: (_) => setState(() {}),
                            ),
                          ),
                          const SizedBox(width: 12),
                          OutlinedButton.icon(
                            onPressed: busy ? null : _browse,
                            icon: const Icon(Icons.folder_open_rounded),
                            label: const Text('Browse…'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      FilledButton.icon(
                        onPressed: (!busy && _selectedDevice != null && _kextPathController.text.trim().isNotEmpty)
                            ? _apply
                            : null,
                        icon: const Icon(Icons.usb_rounded),
                        label: const Text('Apply USB Map'),
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
