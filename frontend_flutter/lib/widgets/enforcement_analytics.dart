import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/theme.dart';

class EnforcementAnalyticsWidget extends StatefulWidget {
  const EnforcementAnalyticsWidget({super.key});

  @override
  State<EnforcementAnalyticsWidget> createState() => _EnforcementAnalyticsWidgetState();
}

class _EnforcementAnalyticsWidgetState extends State<EnforcementAnalyticsWidget> {
  Map<String, dynamic>? _metrics;
  Map<String, dynamic>? _trends;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    try {
      final m = await ApiClient().get('/dashboard/metrics');
      final t = await ApiClient().get('/dashboard/analytics');
      if (mounted) {
        setState(() {
          _metrics = m is Map<String, dynamic> ? m : null;
          _trends = t is Map<String, dynamic> ? t : null;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _metrics == null) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
      );
    }

    if (_metrics == null) return const SizedBox.shrink();

    final compliancePct = _metrics!['compliance_percentage'] ?? 0;
    final compliantCount = _metrics!['compliant_count'] ?? 0;
    final totalInspections = _metrics!['total_inspections'] ?? 0;
    final totalViolations = _metrics!['total_violations'] ?? 0;
    final nonCompliantCount = _metrics!['non_compliant_count'] ?? 0;
    final totalOverrides = _metrics!['total_overrides'] ?? 0;
    final overrideRate = _trends?['override_rate_percentage'] ?? 0;
    final avgOcrConf = _trends?['average_ocr_confidence'] ?? 88.5;

    final topViolations = (_metrics!['top_violations'] as List?) ?? [];
    final categoryBreakdown = (_metrics!['category_breakdown'] as List?) ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 4 KPI Cards
        LayoutBuilder(
          builder: (context, constraints) {
            final isDesktop = constraints.maxWidth >= 800;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _buildKpiCard(
                  title: 'LEGAL COMPLIANCE RATE',
                  value: '$compliancePct%',
                  subtitle: '$compliantCount compliant / $totalInspections total',
                  valueColor: AppTheme.emerald,
                  width: isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                ),
                _buildKpiCard(
                  title: 'VIOLATIONS DETECTED',
                  value: '$totalViolations',
                  subtitle: 'Across $nonCompliantCount non-compliant packages',
                  valueColor: AppTheme.rose,
                  width: isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                ),
                _buildKpiCard(
                  title: 'HUMAN OVERRIDES',
                  value: '$totalOverrides',
                  subtitle: '$overrideRate% human override rate',
                  valueColor: AppTheme.amber,
                  width: isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                ),
                _buildKpiCard(
                  title: 'MEAN OCR CONFIDENCE',
                  value: '$avgOcrConf%',
                  subtitle: 'PaddleOCR text recognition',
                  valueColor: Colors.white,
                  width: isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 16),

        // 2 Column Detailed Sections: Top Violations & Categories
        LayoutBuilder(
          builder: (context, constraints) {
            final isDesktop = constraints.maxWidth >= 900;
            if (isDesktop) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: _buildTopViolationsCard(topViolations)),
                  const SizedBox(width: 16),
                  Expanded(child: _buildCategoryBreakdownCard(categoryBreakdown)),
                ],
              );
            }
            return Column(
              children: [
                _buildTopViolationsCard(topViolations),
                const SizedBox(height: 16),
                _buildCategoryBreakdownCard(categoryBreakdown),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildKpiCard({
    required String title,
    required String value,
    required String subtitle,
    required Color valueColor,
    required double width,
  }) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(16),
      decoration: AppTheme.glassCard(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF94A3B8), letterSpacing: 0.5),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: valueColor, fontFamily: 'monospace'),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
          ),
        ],
      ),
    );
  }

  Widget _buildTopViolationsCard(List<dynamic> violations) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: AppTheme.glassPanel(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: const [
              Text('TOP STATUTORY VIOLATION HOTSPOTS',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
              Text('PCR 2011 Mandates', style: TextStyle(fontSize: 10, color: Color(0xFF64748B), fontFamily: 'monospace')),
            ],
          ),
          const SizedBox(height: 14),
          if (violations.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: Text('No statutory violations recorded in dataset.', style: TextStyle(fontSize: 11, color: Color(0xFF64748B)))),
            )
          else
            ...violations.map((v) {
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF131D31),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(v['title']?.toString() ?? 'Violation', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                decoration: BoxDecoration(
                                  color: const Color(0x33F43F5E),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(v['rule_key']?.toString() ?? '', style: const TextStyle(fontSize: 9, color: AppTheme.rose, fontFamily: 'monospace')),
                              ),
                            ],
                          ),
                          if (v['legal_reference'] != null) ...[
                            const SizedBox(height: 2),
                            Text(v['legal_reference'].toString(), style: const TextStyle(fontSize: 10, color: Color(0xFF64748B), fontStyle: FontStyle.italic)),
                          ],
                        ],
                      ),
                    ),
                    Text(
                      '${v['count'] ?? 0}',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.rose, fontFamily: 'monospace'),
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildCategoryBreakdownCard(List<dynamic> categories) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: AppTheme.glassPanel(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: const [
              Text('COMPLIANCE BY COMMODITY CATEGORY',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
              Text('Enforcement Breakdown', style: TextStyle(fontSize: 10, color: Color(0xFF64748B), fontFamily: 'monospace')),
            ],
          ),
          const SizedBox(height: 14),
          if (categories.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: Text('No categorized inspection records available.', style: TextStyle(fontSize: 11, color: Color(0xFF64748B)))),
            )
          else
            ...categories.map((cat) {
              final total = (cat['total'] as num? ?? 1).toDouble();
              final compliant = (cat['compliant'] as num? ?? 0).toDouble();
              final passPct = total > 0 ? (compliant / total) : 0.0;

              return Container(
                margin: const EdgeInsets.only(bottom: 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(cat['category']?.toString() ?? 'General', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                        Text('${(passPct * 100).toStringAsFixed(0)}% pass · ${total.toInt()} cases',
                            style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontFamily: 'monospace')),
                      ],
                    ),
                    const SizedBox(height: 5),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: passPct,
                        minHeight: 6,
                        backgroundColor: const Color(0x33F43F5E),
                        valueColor: const AlwaysStoppedAnimation(AppTheme.emerald),
                      ),
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}
