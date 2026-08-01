import 'package:flutter/material.dart';

import 'bridge/bridge_client.dart';
import 'home_shell.dart';

class HackMateApp extends StatefulWidget {
  const HackMateApp({super.key});

  @override
  State<HackMateApp> createState() => _HackMateAppState();
}

class _HackMateAppState extends State<HackMateApp> {
  ThemeMode _themeMode = ThemeMode.dark;
  Color _seedColor = const Color(0xFF00E68A);
  late final BridgeClient _bridge;

  @override
  void initState() {
    super.initState();
    _bridge = BridgeClient();
    _bridge.start();
  }

  @override
  void dispose() {
    _bridge.dispose();
    super.dispose();
  }

  void _setThemeMode(ThemeMode mode) {
    setState(() => _themeMode = mode);
  }

  void _setSeedColor(Color color) {
    setState(() => _seedColor = color);
  }

  ThemeData _buildTheme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: _seedColor,
      brightness: brightness,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor:
          brightness == Brightness.dark ? const Color(0xFF0B0F0D) : null,
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        backgroundColor: scheme.inverseSurface,
        contentTextStyle: TextStyle(color: scheme.onInverseSurface),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hackmate',
      debugShowCheckedModeBanner: false,
      themeMode: _themeMode,
      theme: _buildTheme(Brightness.light),
      darkTheme: _buildTheme(Brightness.dark),
      home: HomeShell(
        bridge: _bridge,
        themeMode: _themeMode,
        seedColor: _seedColor,
        onThemeModeChanged: _setThemeMode,
        onSeedColorChanged: _setSeedColor,
      ),
    );
  }
}
