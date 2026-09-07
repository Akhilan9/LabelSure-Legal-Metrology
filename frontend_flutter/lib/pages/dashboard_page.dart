import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../core/api_client.dart';
import '../core/theme.dart';
import '../widgets/enforcement_analytics.dart';
import '../widgets/enforcement_review_queue.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, dynamic>? _summary;
  Map<String, dynamic>? _health;
  bool _summaryLoading = true;
  String _healthState = 'checking';

  final stages = [
    'Capture & OpenCV Quality',
    'PaddleOCR & Extraction',
    'Context & Legal Rules',
    'RuleLens & Officer Review',
    'ReportLab PDF & Audit History',
  ];

  @override
  void initState() {
    super.initState();
    _fetchSummary();
    _checkHealth();
  }

  Future<void> _fetchSummary() async {
    try {
      final res = await ApiClient().get('/dashboard/summary');
      if (mounted) {
        setState(() {
          _summary = res is Map<String, dynamic> ? res : null;
          _summaryLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _summaryLoading = false);
    }
  }

  Future<void> _checkHealth() async {
    setState(() => _healthState = 'checking');
    try {
      final res = await ApiClient().get('/health');
      if (mounted) {
        setState(() {
          _health = res is Map<String, dynamic> ? res : null;
          _healthState = (_health?['status'] == 'ok') ? 'connected' : 'degraded';
        });
      }
    } catch (_) {
      if (mounted) setState(() => _healthState = 'offline');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Hero Banner with Ambient Glow
        _buildHeroBanner(),
        const SizedBox(height: 24),

        // Operational Metrics Grid
        _buildMetricsGrid(),
        const SizedBox(height: 24),

        // Legal Metrology Guideline Failure Justifications
        _buildGuidelineFailureJustificationsCard(),
        const SizedBox(height: 24),

        // Enforcement Analytics
        const EnforcementAnalyticsWidget(),
        const SizedBox(height: 24),

        // Review Queue
        const EnforcementReviewQueueWidget(),
        const SizedBox(height: 24),

        // Recent Inspections Table
        if (_summary != null && (_summary!['recent_inspections'] as List?)?.isNotEmpty == true) ...[
          _buildRecentInspectionsTable(),
          const SizedBox(height: 24),
        ],

        // Pipeline Journey & Health Box Grid
        LayoutBuilder(
          builder: (context, constraints) {
            final isDesktop = constraints.maxWidth >= 900;
            if (isDesktop) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 2, child: _buildPipelineJourneyCard()),
                  const SizedBox(width: 16),
                  Expanded(flex: 1, child: _buildHealthCard()),
                ],
              );
            }
            return Column(
              children: [
                _buildPipelineJourneyCard(),
                const SizedBox(height: 16),
                _buildHealthCard(),
              ],
            );
          },
        ),
        const SizedBox(height: 24),

        // Core Mandates
        _buildMandatesGrid(),
        const SizedBox(height: 32),

        // Footer
        const Center(
          child: Text(
            'APEX LabelSure · Legal Metrology Packaging Compliance Platform · SIH 2026 #26034',
            style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: Color(0xFF475569)),
          ),
        ),
      ],
    );
  }

  Widget _buildHeroBanner() {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: const Color(0xFF131D31),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF1E293B)),
        boxShadow: const [
          BoxShadow(color: Color(0x66000000), blurRadius: 30, offset: Offset(0, 10)),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0x2610B981),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0x4D10B981)),
                  ),
                  child: const Text(
                    '⚡ AI-POWERED COMPLIANCE ENFORCEMENT',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.emerald),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'APEX LabelSure\nLegal Metrology Intelligence',
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    height: 1.15,
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Automated packaging inspection platform for India\'s Legal Metrology (Packaged Commodities) Rules, 2011–2026. Extract statutory declarations, evaluate legal rule compliance, and adjudicate with traceable RuleLens evidence.',
                  style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8), height: 1.6),
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.emerald,
                        foregroundColor: const Color(0xFF090D16),
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      icon: const Icon(Icons.storefront, size: 16),
                      onPressed: () => context.go('/inspection-center'),
                      label: const Text('🏢 Inspection Center', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1E293B),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      onPressed: () => context.go('/inspections/new'),
                      child: const Text('+ Single Inspection', style: TextStyle(fontSize: 12)),
                    ),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: const BorderSide(color: Color(0xFF334155)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      onPressed: () => context.go('/field'),
                      child: const Text('📷 Offline Scanner', style: TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 32),

          // Emblem seal
          Container(
            width: 140,
            height: 140,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0x1A10B981),
              border: Border.all(color: const Color(0x4D10B981), width: 2),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: const [
                Text('L✓', style: TextStyle(fontSize: 36, fontWeight: FontWeight.bold, color: AppTheme.emerald)),
                SizedBox(height: 4),
                Text('SIH 2026 #26034', style: TextStyle(fontSize: 9, fontFamily: 'monospace', color: Color(0xFF64748B), letterSpacing: 1)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGuidelineFailureJustificationsCard() {
    final rawList = _summary?['guideline_failure_justifications'] as List?;
    final justifications = (rawList != null && rawList.isNotEmpty)
        ? rawList.map((e) => e.toString()).toList()
        : <String>[];

    final hasViolations = justifications.isNotEmpty;

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: hasViolations ? const Color(0x80F43F5E) : const Color(0x3310B981),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: hasViolations ? const Color(0x33F43F5E) : const Color(0x1A10B981),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: hasViolations ? const Color(0x33F43F5E) : const Color(0x3310B981),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(
                      hasViolations ? Icons.warning_amber_rounded : Icons.check_circle_outline,
                      color: hasViolations ? AppTheme.rose : AppTheme.emerald,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Legal Metrology Guideline Failure Justifications',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        hasViolations
                            ? 'Statutory non-compliance justifications under PCR Rule 6(1) & Legal Metrology Act, 2009'
                            : 'All processed packages conform with mandatory LMPC Rule 6 statutory declarations.',
                        style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                      ),
                    ],
                  ),
                ],
              ),
              if (hasViolations)
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFFFECDD3),
                    side: const BorderSide(color: Color(0x66F43F5E)),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                  icon: const Icon(Icons.copy, size: 12),
                  label: const Text('Copy All', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: justifications.join('\n')));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Copied failure justifications to clipboard')),
                    );
                  },
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (hasViolations) ...[
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: justifications.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final item = justifications[index];
                return Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E1420),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0x66F43F5E)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 2, right: 8),
                        child: Icon(Icons.error_outline, size: 14, color: AppTheme.rose),
                      ),
                      Expanded(
                        child: SelectableText(
                          item,
                          style: const TextStyle(
                            fontSize: 11,
                            fontFamily: 'monospace',
                            color: Color(0xFFFECDD3),
                            height: 1.4,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        icon: const Icon(Icons.copy, size: 14, color: Color(0xFFFDA4AF)),
                        tooltip: 'Copy justification',
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: item));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Copied to clipboard')),
                          );
                        },
                      ),
                    ],
                  ),
                );
              },
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF062D24),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0x4D10B981)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.verified, size: 16, color: AppTheme.emerald),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Zero active statutory violations: All monitored packaged commodities meet Legal Metrology Rule 6 statutory requirements.',
                      style: TextStyle(fontSize: 11, color: Color(0xFFA7F3D0)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMetricsGrid() {
    final total = _summary?['total_inspections'] ?? 0;
    final drafts = _summary?['draft_count'] ?? 0;
    final staged = _summary?['evidence_uploaded_count'] ?? 0;
    final ready = _summary?['ready_for_analysis_count'] ?? 0;

    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'OPERATIONAL WORKSPACE METRICS',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF64748B), letterSpacing: 1, fontFamily: 'monospace'),
            ),
            InkWell(
              onTap: () => context.go('/inspections'),
              child: const Text('View All Records →', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.emerald)),
            ),
          ],
        ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (context, constraints) {
            final isDesktop = constraints.maxWidth >= 800;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _buildMetricCard('TOTAL RECORDS', '$total', '📁', Colors.white, 'Stored in repository', isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2),
                _buildMetricCard('DRAFTS', '$drafts', '📝', AppTheme.amber, 'Awaiting photo evidence', isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2),
                _buildMetricCard('EVIDENCE STAGED', '$staged', '📸', AppTheme.cyan, 'Uploaded & quality assessed', isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2),
                _buildMetricCard('READY FOR RULES', '$ready', '⚡', AppTheme.emerald, 'Queued for rule evaluation', isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildMetricCard(String title, String value, String icon, Color valColor, String subtitle, double width) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(16),
      decoration: AppTheme.glassCard(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF94A3B8))),
              Text(icon, style: const TextStyle(fontSize: 14)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _summaryLoading ? '…' : value,
            style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: valColor, fontFamily: 'monospace'),
          ),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(fontSize: 10, color: Color(0xFF64748B))),
        ],
      ),
    );
  }

  Widget _buildRecentInspectionsTable() {
    final recent = (_summary!['recent_inspections'] as List?) ?? [];

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Recent Inspection Activity',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
              InkWell(
                onTap: () => context.go('/inspections'),
                child: const Text('Full Case Explorer →', style: TextStyle(fontSize: 11, color: AppTheme.emerald, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              headingRowHeight: 36,
              dataRowMinHeight: 44,
              dataRowMaxHeight: 52,
              columns: const [
                DataColumn(label: Text('CODE')),
                DataColumn(label: Text('COMMODITY NAME')),
                DataColumn(label: Text('STATUS')),
                DataColumn(label: Text('PHOTOS')),
                DataColumn(label: Text('ACTION')),
              ],
              rows: recent.map((insp) {
                final id = insp['id']?.toString() ?? '';
                return DataRow(
                  cells: [
                    DataCell(Text(insp['inspection_code']?.toString() ?? '',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, fontFamily: 'monospace', color: AppTheme.emerald))),
                    DataCell(Text(insp['product_name']?.toString() ?? '—', style: const TextStyle(fontSize: 11, color: Colors.white))),
                    DataCell(Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(4)),
                      child: Text(insp['status']?.toString() ?? '', style: const TextStyle(fontSize: 9, color: Color(0xFFCBD5E1))),
                    )),
                    DataCell(Text('${insp['images_count'] ?? 0} panels', style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)))),
                    DataCell(
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0x2610B981),
                          foregroundColor: AppTheme.emerald,
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                        ),
                        onPressed: () => context.go('/inspections/$id'),
                        child: const Text('Open Workspace →', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPipelineJourneyCard() {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: const [
              Text('Regulatory Inspection Pipeline',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
              Text('LMPC 2011–2026', style: TextStyle(fontSize: 10, color: Color(0xFF64748B), fontFamily: 'monospace')),
            ],
          ),
          const SizedBox(height: 4),
          const Text('Traceable workflow progression from raw package evidence to court-admissible certificates.',
              style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
          const SizedBox(height: 14),
          ...stages.asMap().entries.map((e) {
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
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: const Color(0x3310B981),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0x6610B981)),
                    ),
                    child: Center(
                      child: Text('0${e.key + 1}',
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.emerald, fontFamily: 'monospace')),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(e.value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white)),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(color: const Color(0xFF065F46), borderRadius: BorderRadius.circular(4)),
                    child: const Text('Operational', style: TextStyle(fontSize: 9, color: AppTheme.emerald, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildHealthCard() {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('API Engine Status', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _healthState == 'connected' ? const Color(0x3310B981) : const Color(0x33F43F5E),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  _healthState.toUpperCase(),
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    fontFamily: 'monospace',
                    color: _healthState == 'connected' ? AppTheme.emerald : AppTheme.rose,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildHealthRow('Service', 'FastAPI Backend'),
          _buildHealthRow('OCR Engine', 'PaddleOCR PP-OCRv6'),
          _buildHealthRow('Database', _health?['database']?.toString() ?? 'SQLite / Postgres'),
          _buildHealthRow('Report Engine', 'ReportLab PDF'),
          const SizedBox(height: 16),
          OutlinedButton(
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.white,
              side: const BorderSide(color: Color(0xFF334155)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              padding: const EdgeInsets.symmetric(vertical: 10),
            ),
            onPressed: _healthState == 'checking' ? null : _checkHealth,
            child: const Text('Re-verify API Connection 🔄', style: TextStyle(fontSize: 11)),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthRow(String title, String val) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
          Text(val, style: const TextStyle(fontSize: 11, fontFamily: 'monospace', fontWeight: FontWeight.bold, color: Colors.white)),
        ],
      ),
    );
  }

  Widget _buildMandatesGrid() {
    final mandates = [
      ('01', 'AI Observes', 'OCR models localize visible declarations as evidence.'),
      ('02', 'Rules Decide', 'Versioned legal rulesets enforce LMPC requirements.'),
      ('03', 'Evidence Explains', 'RuleLens links findings to photographic coordinates.'),
      ('04', 'Inspector Verifies', 'Officers maintain accountable adjudication overrides.'),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final isDesktop = constraints.maxWidth >= 800;
        final w = isDesktop ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2;

        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: mandates.map((m) {
            return Container(
              width: w,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0x33131D31),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(m.$1, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.emerald, fontFamily: 'monospace')),
                  const SizedBox(height: 4),
                  Text(m.$2, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                  const SizedBox(height: 2),
                  Text(m.$3, style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8), height: 1.4)),
                ],
              ),
            );
          }).toList(),
        );
      },
    );
  }
}
