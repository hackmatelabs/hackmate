import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';

class LogCheckerScreen extends StatefulWidget {
  final BridgeClient bridge;

  const LogCheckerScreen({super.key, required this.bridge});

  @override
  State<LogCheckerScreen> createState() => _LogCheckerScreenState();
}

class _LogCheckerScreenState extends State<LogCheckerScreen> {
  final _pathController = TextEditingController();
  Future<List<dynamic>>? _future;

  void _analyze() {
    final path = _pathController.text.trim();
    if (path.isEmpty) return;
    setState(() {
      _future = widget.bridge
          .call('log_checker.analyze_file', {'path': path}).then((r) => r as List<dynamic>);
    });
  }

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  Color _severityColor(ColorScheme scheme, String severity) {
    switch (severity) {
      case 'critical':
        return scheme.error;
      case 'warning':
        return Colors.amber;
      default:
        return scheme.onSurfaceVariant;
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
          Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: scheme.secondaryContainer,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Icon(Icons.receipt_long_rounded, size: 28, color: scheme.onSecondaryContainer),
              ),
              const SizedBox(width: 16),
              Text(
                'Check Logs',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _pathController,
                  decoration: const InputDecoration(
                    labelText: 'Log file path',
                    hintText: r'C:\path\to\opencore.log or panic.log',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (_) => _analyze(),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: _analyze,
                icon: const Icon(Icons.search_rounded),
                label: const Text('Analyze'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Expanded(
            child: _future == null
                ? Center(
                    child: Text(
                      'Enter a log file path to analyze.',
                      style: TextStyle(color: scheme.onSurfaceVariant),
                    ),
                  )
                : FutureBuilder<List<dynamic>>(
                    future: _future,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState != ConnectionState.done) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (snapshot.hasError) {
                        return Center(
                          child: Text(
                            snapshot.error is BridgeException
                                ? (snapshot.error as BridgeException).message
                                : snapshot.error.toString(),
                            style: TextStyle(color: scheme.error),
                          ),
                        );
                      }
                      final findings = snapshot.data!;
                      if (findings.isEmpty) {
                        return const Center(child: Text('No issues found.'));
                      }
                      return ListView.separated(
                        itemCount: findings.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 8),
                        itemBuilder: (context, index) {
                          final f = findings[index] as Map<String, dynamic>;
                          final severity = f['severity'] as String? ?? 'info';
                          final fixSteps = (f['fix_steps'] as List<dynamic>? ?? []).cast<String>();
                          return Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Container(
                                        width: 10,
                                        height: 10,
                                        decoration: BoxDecoration(
                                          color: _severityColor(scheme, severity),
                                          shape: BoxShape.circle,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          f['title'] as String? ?? '',
                                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                                fontWeight: FontWeight.w600,
                                              ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(f['explanation'] as String? ?? ''),
                                  if (fixSteps.isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    for (final step in fixSteps)
                                      Text('• $step', style: TextStyle(color: scheme.onSurfaceVariant)),
                                  ],
                                ],
                              ),
                            ),
                          );
                        },
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
