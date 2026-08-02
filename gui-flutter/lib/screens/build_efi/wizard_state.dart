import 'package:flutter/material.dart';

import '../../bridge/bridge_client.dart';

enum WizardStep {
  hardware,
  manualHardware,
  version,
  usbTarget,
  buildMode,
  wifiKext,
  gpuChoice,
  dgpu,
  dualBoot,
  confirm,
  install,
  biosChecklist,
}

class WizardState extends ChangeNotifier {
  final BridgeClient bridge;
  final bool manual;

  WizardState({required this.bridge, required this.manual})
      : step = manual ? WizardStep.manualHardware : WizardStep.hardware;

  WizardStep step;
  final List<WizardStep> backStack = [];

  bool loading = false;
  String? error;

  Map<String, dynamic>? manualOptions;

  Map<String, dynamic>? profile;
  List<String> profileWarnings = [];
  bool needsDgpuPrompt = false;

  List<dynamic> versions = [];
  Map<String, dynamic>? macosVersion;

  List<dynamic> drives = [];
  String? device;
  String? localOutputPath;

  bool repair = false;
  bool skipFormat = false;
  String wifiKextMode = 'itlwm';
  bool disableDgpu = false;
  String dualBoot = '';

  bool installRunning = false;
  bool installDone = false;
  bool installOk = false;
  String? installError;
  int installPct = 0;
  String installMessage = '';
  final List<Map<String, String>> installLog = [];
  Map<String, dynamic>? installResult;

  void goTo(WizardStep next, {bool pushCurrent = true}) {
    if (pushCurrent) backStack.add(step);
    step = next;
    error = null;
    notifyListeners();
  }

  void restart() {
    installDone = false;
    installResult = null;
    installLog.clear();
    backStack.clear();
    step = WizardStep.hardware;
    notifyListeners();
  }

  void back() {
    if (backStack.isEmpty) return;
    step = backStack.removeLast();
    error = null;
    notifyListeners();
  }

  Future<void> loadManualOptions() async {
    if (manualOptions != null) return;
    loading = true;
    notifyListeners();
    try {
      manualOptions = await bridge.call('hardware.manual_options');
    } catch (e) {
      error = e is BridgeException ? e.message : e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> _afterProfileReady() async {
    try {
      final warningsResult = await bridge.call('hardware.warnings', {'profile': profile});
      profileWarnings = (warningsResult['warnings'] as List).cast<String>();
      final dgpuResult = await bridge.call('hardware.needs_dgpu_prompt', {'profile': profile});
      needsDgpuPrompt = dgpuResult['needed'] == true;
    } catch (e) {
      error = e is BridgeException ? e.message : e.toString();
    }
  }

  Future<void> runScan() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      profile = await bridge.call('hardware.scan') as Map<String, dynamic>;
      await _afterProfileReady();
      loading = false;
      notifyListeners();
    } catch (e) {
      loading = false;
      error = e is BridgeException ? e.message : e.toString();
      notifyListeners();
    }
  }

  Future<void> submitManualProfile({
    required String cpuKey,
    required String gpuKey,
    required String ethKey,
    required String wifiKey,
    required bool isLaptop,
    required int cores,
    required String audioCodec,
    required bool nvmePresent,
    required bool hasThunderbolt,
  }) async {
    final opts = manualOptions!;
    final cpuMeta = (opts['cpu_meta'] as Map<String, dynamic>)[cpuKey] as List<dynamic>;
    final gen = cpuMeta[0] as int;
    final codename = cpuMeta[1] as String;
    final vendor = cpuMeta[2] as String;
    final ocPlatform = cpuMeta[3] as String;

    String gpuVendor = 'intel';
    if (gpuKey == 'amd') {
      gpuVendor = 'amd';
    } else if (gpuKey == 'nvidia') {
      gpuVendor = 'nvidia';
    }
    final gpuOptions = (opts['gpu_options'] as List).cast<List<dynamic>>();
    final gpuLabel = gpuOptions.firstWhere((o) => o[0] == gpuKey, orElse: () => ['', ''])[1] as String;
    final platform = isLaptop ? 'laptop' : 'desktop';
    final smbiosMap = opts['smbios_map'] as Map<String, dynamic>;
    final smbiosModel = smbiosMap['$gen|$platform'] as String? ?? '';

    profile = {
      'cpu_name': '${vendor[0].toUpperCase()}${vendor.substring(1)} $codename',
      'cpu_vendor': vendor,
      'cpu_generation': gen,
      'cpu_codename': codename,
      'oc_platform': ocPlatform,
      'core_count': cores,
      'gpu_vendor': gpuVendor,
      'gpu_name': gpuLabel,
      'gpu_device_id': (gpuKey == 'amd' || gpuKey == 'nvidia' || gpuKey == '') ? '' : gpuKey,
      'audio_codec': audioCodec.toUpperCase(),
      'ethernet_chipset': ethKey,
      'wifi_chipset': wifiKey,
      'platform': platform,
      'nvme_present': nvmePresent,
      'has_thunderbolt': hasThunderbolt,
      'has_touchpad': isLaptop,
      'smbios_model': smbiosModel,
    };

    loading = true;
    notifyListeners();
    await _afterProfileReady();
    loading = false;
    notifyListeners();
    goTo(WizardStep.version);
  }

  Future<void> loadVersions() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final p = profile!;
      final r = await bridge.call('recovery.compatible_versions', {
        'cpu_gen': p['cpu_generation'] ?? 0,
        'gpu_vendor': p['gpu_vendor'] ?? '',
        'cpu_vendor': p['cpu_vendor'] ?? 'intel',
        'cpu_codename': p['cpu_codename'] ?? '',
        'gpu_name': p['gpu_name'] ?? '',
      });
      versions = r['versions'] as List<dynamic>;
    } catch (e) {
      error = e is BridgeException ? e.message : e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void selectVersion(Map<String, dynamic> v) {
    macosVersion = v;
    goTo(WizardStep.usbTarget);
  }

  Future<void> loadDrives() async {
    loading = true;
    notifyListeners();
    try {
      final r = await bridge.call('usb.list_drives');
      drives = r['drives'] as List<dynamic>;
    } catch (e) {
      error = e is BridgeException ? e.message : e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void selectUsbDevice(String d) {
    device = d;
    localOutputPath = null;
    goTo(WizardStep.buildMode);
  }

  void selectLocalOutput(String path) {
    device = 'local';
    localOutputPath = path;
    repair = false;
    skipFormat = true;
    goTo(WizardStep.dualBoot);
  }

  void _afterBuildMode() {
    final wifiChipset = profile?['wifi_chipset'] as String? ?? '';
    if (wifiChipset.isNotEmpty) {
      goTo(WizardStep.wifiKext);
    } else if (needsDgpuPrompt) {
      goTo(WizardStep.gpuChoice);
    } else {
      goTo(WizardStep.dualBoot);
    }
  }

  void selectBuildMode(bool r, bool sf) {
    repair = r;
    skipFormat = sf;
    _afterBuildMode();
  }

  void _afterWifiKext() {
    if (needsDgpuPrompt) {
      goTo(WizardStep.gpuChoice);
    } else {
      goTo(WizardStep.dualBoot);
    }
  }

  void selectWifiKextMode(String mode) {
    wifiKextMode = mode;
    _afterWifiKext();
  }

  void selectSupportedGpu() {
    disableDgpu = true;
    goTo(WizardStep.dualBoot);
  }

  void selectUnsupportedGpu() {
    goTo(WizardStep.dgpu);
  }

  void selectDgpuChoice(bool disable) {
    disableDgpu = disable;
    goTo(WizardStep.dualBoot);
  }

  void selectDualBoot(String choice) {
    dualBoot = choice;
    goTo(WizardStep.confirm);
  }

  String get expectedConfirmPhrase => 'WRITE ${device ?? ''}';

  Future<void> runBuild(String confirmPhrase) async {
    installRunning = true;
    installDone = false;
    installLog.clear();
    installPct = 0;
    installMessage = 'Starting...';
    notifyListeners();
    goTo(WizardStep.install);

    try {
      final result = await bridge.callStreaming(
        'build.run',
        {
          'profile': profile,
          'macos_version': macosVersion,
          'device': device,
          'repair': repair,
          'skip_format': skipFormat,
          'wifi_kext_mode': wifiKextMode,
          'disable_dgpu': disableDgpu,
          'dual_boot': dualBoot,
          'local_output_path': localOutputPath ?? '',
          'confirm_phrase': confirmPhrase,
        },
        (event) {
          final data = event.data as Map<String, dynamic>?;
          if (data == null) return;
          if (event.method == 'progress') {
            installPct = data['pct'] as int? ?? installPct;
            installMessage = data['message']?.toString() ?? installMessage;
          } else if (event.method == 'log') {
            installLog.add({
              'level': data['level']?.toString() ?? 'info',
              'message': data['message']?.toString() ?? '',
            });
          }
          notifyListeners();
        },
      );
      installResult = result as Map<String, dynamic>;
      installOk = true;
      installDone = true;
      installRunning = false;
      notifyListeners();
      if (installResult?['show_bios_checklist'] == true) {
        goTo(WizardStep.biosChecklist);
      }
    } catch (e) {
      installOk = false;
      installDone = true;
      installRunning = false;
      installError = e is BridgeException ? e.message : e.toString();
      notifyListeners();
    }
  }
}
