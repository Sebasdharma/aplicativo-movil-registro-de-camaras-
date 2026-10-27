import 'package:flutter/material.dart';

import '../core/constants/app_colors.dart';

class InstitutionalEvaView extends StatelessWidget {
  final VoidCallback onGuestAccess;

  const InstitutionalEvaView({super.key, required this.onGuestAccess});

  void _showMicrosoftNotice(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'El inicio de sesión real de Microsoft 365 requiere configurar la aplicación institucional.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(14, 18, 14, 16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            children: [
              Container(
                width: 56,
                height: 56,
                margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(
                  color: AppColors.upecGreen,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.upecYellow, width: 2),
                ),
                child: const Icon(
                  Icons.school,
                  color: Colors.white,
                  size: 30,
                ),
              ),
              const Text(
                'Entorno Virtual de Aprendizaje UPEC',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 3),
              const Text(
                'Campus Tulcán • aulas-virtuales.upec.edu.ec',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 18),
              const Divider(color: AppColors.border),
              const Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Identifíquese usando su cuenta en:',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => _showMicrosoftNotice(context),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.textPrimary,
                    side: const BorderSide(color: AppColors.borderDark),
                    padding: const EdgeInsets.symmetric(vertical: 11),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  icon: const _MicrosoftMark(),
                  label: const Text(
                    'Microsoft 365',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 14, bottom: 6),
                child: Text(
                  'Algunos cursos permiten el acceso de invitados:',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onGuestAccess,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.upecGreen,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  child: const Text(
                    'Entrar como persona invitada',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MicrosoftMark extends StatelessWidget {
  const _MicrosoftMark();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 18,
      height: 18,
      child: Column(
        children: [
          Expanded(
            child: Row(
              children: [
                Expanded(child: ColoredBox(color: Color(0xFFF25022))),
                SizedBox(width: 2),
                Expanded(child: ColoredBox(color: Color(0xFF7FBA00))),
              ],
            ),
          ),
          SizedBox(height: 2),
          Expanded(
            child: Row(
              children: [
                Expanded(child: ColoredBox(color: Color(0xFF00A4EF))),
                SizedBox(width: 2),
                Expanded(child: ColoredBox(color: Color(0xFFFFB900))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
