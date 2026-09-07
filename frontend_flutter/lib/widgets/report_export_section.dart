import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:universal_html/html.dart' as html;
import '../core/api_client.dart';
import '../core/theme.dart';

class ReportExportSection extends StatefulWidget {
  final Map<String, dynamic> inspection;

  const ReportExportSection({super.key, required this.inspection});

  @override
  State<ReportExportSection> createState() => _ReportExportSectionState();
}

class _ReportExportSectionState extends State<ReportExportSection> {
  Map<String, dynamic>? _summary;
  String? _downloadingFormat;
  bool _copiedHash = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final id = widget.inspection['id'];
      final res = await ApiClient().get('/inspections/$id/reports/summary');
      if (mounted) {
        setState(() {
          _summary = res is Map<String, dynamic> ? res : null;
        });
      }
    } catch (_) {}
  }

  Future<void> _download(String path, String filename, String format) async {
    setState(() => _downloadingFormat = format);
    try {
      final bytes = await ApiClient().getBytes(path);
      if (kIsWeb) {
        final blob = html.Blob([bytes]);
        final url = html.Url.createObjectUrlFromBlob(blob);
        html.AnchorElement(href: url)
          ..setAttribute('download', filename)
          ..click();
        html.Url.revokeObjectUrl(url);
      }
    } catch (_) {}
    if (mounted) setState(() => _downloadingFormat = null);
  }

  void _showJsonModal() async {
    final id = widget.inspection['id'];
    dynamic jsonData;
    try {
      jsonData = await ApiClient().get('/inspections/$id/reports/json');
    } catch (_) {
      return;
    }

    if (!mounted) return;
    showDialog(
      context: context,
      builder: (ctx) {
        final prettyJson = const JsonEncoder.withIndent('  ').convert(jsonData);
        return AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Complete Case JSON Snapshot', style: TextStyle(color: Colors.white, fontSize: 13)),
          content: SizedBox(
            width: 700,
            height: 480,
            child: SingleChildScrollView(
              child: SelectableText(
                prettyJson,
                style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: Color(0xFFCBD5E1)),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: prettyJson));
                Navigator.of(ctx).pop();
              },
              child: const Text('Copy JSON', style: TextStyle(color: AppTheme.emerald)),
            ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Close', style: TextStyle(color: Colors.white)),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final code = widget.inspection['inspection_code'] ?? 'case';
    final id = widget.inspection['id'];
    final tamperHash = _summary?['tamper_sha256']?.toString() ?? widget.inspection['tamper_hash']?.toString() ?? 'SEALED-INTEGRITY-SHA256-PENDING';

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: const [
              Text(
                'STATUTORY REPORTS & EVIDENTIARY EXPORTS',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
              ),
              Spacer(),
              Text('ReportLab PDF · RFC-4180 CSV · JSON-LD',
                  style: TextStyle(fontSize: 10, color: Color(0xFF64748B), fontFamily: 'monospace')),
            ],
          ),
          const SizedBox(height: 14),

          // Tamper Hash Box
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Row(
              children: [
                const Text('🔒 TAMPER-EVIDENT EVIDENCE SEAL: ',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.emerald)),
                Expanded(
                  child: Text(
                    tamperHash,
                    style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: Color(0xFFCBD5E1)),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                IconButton(
                  icon: Icon(_copiedHash ? Icons.check : Icons.copy, size: 14, color: AppTheme.emerald),
                  tooltip: 'Copy SHA-256 hash',
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: tamperHash));
                    setState(() => _copiedHash = true);
                    Future.delayed(const Duration(seconds: 2), () {
                      if (mounted) setState(() => _copiedHash = false);
                    });
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Legal Metrology Guideline Failure Justifications Included In Report
          Builder(
            builder: (context) {
              final rawList = _summary?['guideline_failure_justifications'] as List?;
              final justifications = (rawList != null && rawList.isNotEmpty)
                  ? rawList.map((e) => e.toString()).toList()
                  : <String>[];
              if (justifications.isEmpty) return const SizedBox.shrink();
              return Column(
                children: [
                  _buildJustificationsReportPreview(justifications),
                  const SizedBox(height: 16),
                ],
              );
            },
          ),

          // Export Action Buttons
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.emerald,
                  foregroundColor: const Color(0xFF090D16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                icon: _downloadingFormat == 'PDF'
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Icon(Icons.picture_as_pdf, size: 18),
                label: const Text('Download Official PDF Report', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                onPressed: () => _download('/inspections/$id/reports/pdf', 'LabelSure_Statutory_Report_$code.pdf', 'PDF'),
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF334155)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                ),
                icon: const Icon(Icons.table_chart, size: 16, color: Color(0xFF94A3B8)),
                label: const Text('Export Violations CSV', style: TextStyle(fontSize: 11)),
                onPressed: () => _download('/inspections/$id/reports/csv?target=rules', 'LabelSure_Violations_$code.csv', 'CSV'),
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF334155)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                ),
                icon: const Icon(Icons.list_alt, size: 16, color: Color(0xFF94A3B8)),
                label: const Text('Export Declarations CSV', style: TextStyle(fontSize: 11)),
                onPressed: () => _download('/inspections/$id/reports/csv?target=declarations', 'LabelSure_Declarations_$code.csv', 'CSV2'),
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF334155)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                ),
                icon: const Icon(Icons.data_object, size: 16, color: Color(0xFF94A3B8)),
                label: const Text('View Case JSON', style: TextStyle(fontSize: 11)),
                onPressed: _showJsonModal,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildJustificationsReportPreview(List<String> justifications) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E1014),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x80F43F5E), width: 1.5),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0x33F43F5E),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Icon(Icons.picture_as_pdf, color: AppTheme.rose, size: 16),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'Legal Metrology Guideline Failure Justifications',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Embedded in official statutory report, legal notice, and evidentiary export datasets',
                        style: TextStyle(fontSize: 10, color: Color(0xFFCBD5E1)),
                      ),
                    ],
                  ),
                ],
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFFECDD3),
                  side: const BorderSide(color: Color(0x66F43F5E)),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                ),
                icon: const Icon(Icons.copy, size: 12),
                label: const Text('Copy Justifications', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                onPressed: () {
                  final text = "Legal Metrology Guideline Failure Justifications\n${justifications.join('\n')}";
                  Clipboard.setData(ClipboardData(text: text));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Copied Legal Metrology Guideline Failure Justifications to clipboard')),
                  );
                },
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0x66F43F5E)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: justifications.map((j) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: SelectableText(
                    j,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 11,
                      color: Color(0xFFFECDD3),
                      height: 1.4,
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
}
