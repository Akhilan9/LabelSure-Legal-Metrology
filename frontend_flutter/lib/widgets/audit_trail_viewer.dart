import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/theme.dart';

class AuditTrailViewerWidget extends StatefulWidget {
  final Map<String, dynamic> inspection;

  const AuditTrailViewerWidget({super.key, required this.inspection});

  @override
  State<AuditTrailViewerWidget> createState() => _AuditTrailViewerWidgetState();
}

class _AuditTrailViewerWidgetState extends State<AuditTrailViewerWidget> {
  List<dynamic> _events = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final id = widget.inspection['id'];
      final res = await ApiClient().get('/inspections/$id/audit-trail');
      if (mounted) {
        setState(() {
          _events = res is List ? res : [];
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: const [
              Text(
                'CHAIN OF CUSTODY & AUDIT LOG',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
              ),
              Spacer(),
              Text('Immutable Audit Trail',
                  style: TextStyle(fontSize: 10, color: Color(0xFF64748B), fontFamily: 'monospace')),
            ],
          ),
          const SizedBox(height: 14),

          if (_loading)
            const Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2))
          else if (_events.isEmpty)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('No audit events logged yet.', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _events.length,
              separatorBuilder: (_, _) => const Divider(color: Color(0xFF1E293B), height: 16),
              itemBuilder: (context, i) {
                final e = _events[i] as Map<String, dynamic>;
                final type = e['event_type']?.toString() ?? 'SYSTEM_EVENT';
                final time = e['created_at']?.toString() ?? '';
                final user = e['actor_email']?.toString() ?? e['actor_id']?.toString() ?? 'System';

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      margin: const EdgeInsets.only(top: 4),
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: AppTheme.emerald,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(type.replaceAll('_', ' '),
                                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                              const Spacer(),
                              Text(time, style: const TextStyle(fontSize: 10, color: Color(0xFF64748B), fontFamily: 'monospace')),
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text('By $user', style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8))),
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }
}
