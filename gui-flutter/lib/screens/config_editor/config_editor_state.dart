import 'package:flutter/material.dart';

import '../../bridge/bridge_client.dart';

enum ConfigEditorTab { simple, advanced }

class ConfigEditorState extends ChangeNotifier {
  final BridgeClient bridge;
  final String path;
  String? sessionId;

  bool loading = true;
  String? error;
  ConfigEditorTab tab = ConfigEditorTab.simple;
  bool saving = false;
  String? saveMessage;
  bool saveOk = true;

  List<List<dynamic>> kexts = [];
  List<List<dynamic>> acpi = [];
  Map<String, dynamic> bootArgs = {};
  Map<String, dynamic> bootArgPresets = {};

  bool sipEnabled = true;
  bool hideAuxiliary = true;
  bool ocLogging = false;
  int timeout = 5;
  bool dgpuDisabled = false;
  String igpuPlatformId = '';

  final secureBootModelController = TextEditingController();
  final smbiosModelController = TextEditingController();
  final serialController = TextEditingController();
  final mlbController = TextEditingController();
  final uuidController = TextEditingController();
  final romController = TextEditingController();
  final igpuHexController = TextEditingController();
  final gpuDeviceIdController = TextEditingController();
  final audioCodecController = TextEditingController();
  final rawPathController = TextEditingController();
  final rawValueController = TextEditingController();
  String rawType = 'string';

  List<List<dynamic>> framebufferSuggestions = [];
  List<List<dynamic>> audioLayoutSuggestions = [];
  final List<String> changeLog = [];

  ConfigEditorState({required this.bridge, required this.path});

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final constants = await bridge.call('config_editor.constants');
      final opened = await bridge.call('config_editor.open', {'path': path});
      sessionId = opened['session_id'] as String;
      final summary = opened['summary'] as Map<String, dynamic>;
      bootArgPresets = constants['boot_arg_presets'] as Map<String, dynamic>;
      kexts = (summary['kexts'] as List).cast<List<dynamic>>();
      acpi = (summary['acpi'] as List).cast<List<dynamic>>();
      bootArgs = Map<String, dynamic>.from(summary['boot_args'] as Map);
      final serial = summary['serial'] as Map<String, dynamic>;
      serialController.text = serial['serial'] as String? ?? '';
      mlbController.text = serial['mlb'] as String? ?? '';
      uuidController.text = serial['uuid'] as String? ?? '';
      romController.text = serial['rom'] as String? ?? '';
      sipEnabled = summary['sip_enabled'] == true;
      hideAuxiliary = summary['hide_auxiliary'] == true;
      timeout = summary['timeout'] as int? ?? 5;
      ocLogging = summary['oc_logging'] == true;
      secureBootModelController.text = summary['secure_boot_model'] as String? ?? '';
      smbiosModelController.text = summary['smbios_model'] as String? ?? '';
      dgpuDisabled = summary['dgpu_disabled'] == true;
      igpuPlatformId = summary['igpu_platform_id'] as String? ?? '';
      igpuHexController.text = igpuPlatformId;
    } catch (e) {
      error = e is BridgeException ? e.message : e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> toggleKext(String name, bool enabled) async {
    final idx = kexts.indexWhere((k) => k[0] == name);
    if (idx != -1) {
      final prev = kexts[idx][1] as bool;
      kexts[idx][1] = enabled;
      notifyListeners();
      try {
        await bridge.call('config_editor.set_kext_enabled', {
          'session_id': sessionId,
          'name': name,
          'enabled': enabled,
        });
      } catch (_) {
        kexts[idx][1] = prev;
        notifyListeners();
      }
    }
  }

  Future<void> toggleAcpi(String name, bool enabled) async {
    final idx = acpi.indexWhere((a) => a[0] == name);
    if (idx != -1) {
      final prev = acpi[idx][1] as bool;
      acpi[idx][1] = enabled;
      notifyListeners();
      try {
        await bridge.call('config_editor.set_acpi_enabled', {
          'session_id': sessionId,
          'name': name,
          'enabled': enabled,
        });
      } catch (_) {
        acpi[idx][1] = prev;
        notifyListeners();
      }
    }
  }

  void setTab(ConfigEditorTab t) {
    tab = t;
    notifyListeners();
  }

  void setOcLogging(bool v) {
    ocLogging = v;
    notifyListeners();
  }

  void setSipEnabled(bool v) {
    sipEnabled = v;
    notifyListeners();
  }

  void setDgpuDisabled(bool v) {
    dgpuDisabled = v;
    notifyListeners();
  }

  void applyPreset(String name) {
    final preset = bootArgPresets[name] as Map<String, dynamic>?;
    if (preset == null) return;
    bootArgs = {...bootArgs, ...preset};
    notifyListeners();
  }

  void removeBootArg(String key) {
    bootArgs = {...bootArgs}..remove(key);
    notifyListeners();
  }

  void addBootArg(String key, String value) {
    if (key.trim().isEmpty) return;
    bootArgs = {...bootArgs, key.trim(): value.trim().isEmpty ? true : value.trim()};
    notifyListeners();
  }

  Future<void> applySerialInfo() async {
    try {
      await bridge.call('config_editor.set_serial_info', {
        'session_id': sessionId,
        'serial': serialController.text,
        'mlb': mlbController.text,
        'uuid': uuidController.text,
        'rom': romController.text,
      });
      changeLog.add('Applied serial info');
      notifyListeners();
    } catch (e) {
      changeLog.add('Failed to apply serial info: $e');
      notifyListeners();
    }
  }

  Future<void> applyIgpuHex(String hex) async {
    if (hex.trim().isEmpty) return;
    try {
      await bridge.call('config_editor.set_igpu_platform_id', {'session_id': sessionId, 'hex': hex.trim()});
      igpuPlatformId = hex.trim();
      igpuHexController.text = hex.trim();
      changeLog.add('Set iGPU platform-id to $hex');
      notifyListeners();
    } catch (e) {
      changeLog.add('Failed to set iGPU platform-id: $e');
      notifyListeners();
    }
  }

  Future<void> suggestFramebuffers() async {
    try {
      final r = await bridge.call('config_editor.suggest_framebuffers', {
        'gpu_device_id': gpuDeviceIdController.text.trim(),
      });
      framebufferSuggestions = (r['suggestions'] as List).cast<List<dynamic>>();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> suggestAudioLayouts() async {
    try {
      final r = await bridge.call('config_editor.suggest_audio_layouts', {
        'codec': audioCodecController.text.trim(),
      });
      audioLayoutSuggestions = (r['suggestions'] as List).cast<List<dynamic>>();
      notifyListeners();
    } catch (_) {}
  }

  void applyAudioLayout(int layoutId) {
    bootArgs = {...bootArgs, 'alcid': layoutId.toString()};
    notifyListeners();
  }

  Future<void> getRawValue() async {
    try {
      final r = await bridge.call('config_editor.get_raw_value', {
        'session_id': sessionId,
        'path': rawPathController.text.trim(),
      });
      rawType = r['type'] as String? ?? 'string';
      rawValueController.text = '${r['value']}';
      notifyListeners();
    } catch (e) {
      changeLog.add('Get failed: $e');
      notifyListeners();
    }
  }

  Future<void> setRawValue() async {
    try {
      await bridge.call('config_editor.set_raw_value', {
        'session_id': sessionId,
        'path': rawPathController.text.trim(),
        'value': rawValueController.text,
        'type': rawType,
      });
      changeLog.add('Set ${rawPathController.text.trim()} = ${rawValueController.text} ($rawType)');
      if (changeLog.length > 8) changeLog.removeAt(0);
      notifyListeners();
    } catch (e) {
      changeLog.add('Set failed: $e');
      notifyListeners();
    }
  }

  Future<bool> save() async {
    saving = true;
    saveMessage = null;
    notifyListeners();
    try {
      await bridge.call('config_editor.set_simple', {
        'session_id': sessionId,
        'sip_enabled': sipEnabled,
        'hide_auxiliary': hideAuxiliary,
        'timeout': timeout,
        'oc_logging': ocLogging,
        'secure_boot_model': secureBootModelController.text,
        'smbios_model': smbiosModelController.text,
      });
      await bridge.call('config_editor.set_boot_args', {'session_id': sessionId, 'args': bootArgs});
      await bridge.call('config_editor.set_dgpu_disabled', {'session_id': sessionId, 'disabled': dgpuDisabled});
      await bridge.call('config_editor.save', {'session_id': sessionId});
      saveOk = true;
      saveMessage = 'Saved.';
      return true;
    } catch (e) {
      saveOk = false;
      saveMessage = e is BridgeException ? e.message : e.toString();
      return false;
    } finally {
      saving = false;
      notifyListeners();
    }
  }

  void close() {
    final sid = sessionId;
    if (sid != null) {
      bridge.call('config_editor.close', {'session_id': sid}).catchError((_) => null);
    }
  }

  @override
  void dispose() {
    secureBootModelController.dispose();
    smbiosModelController.dispose();
    serialController.dispose();
    mlbController.dispose();
    uuidController.dispose();
    romController.dispose();
    igpuHexController.dispose();
    gpuDeviceIdController.dispose();
    audioCodecController.dispose();
    rawPathController.dispose();
    rawValueController.dispose();
    super.dispose();
  }
}
