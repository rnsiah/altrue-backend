from django.db import migrations


def seed_default_levels(apps, schema_editor):
    """Seed the default AltrueLevel ladder so profile-creation signals
    (which expect level_number=0) work in any fresh environment,
    including the test database. Audit fix: Phase 0, 2026-10-14."""
    AltrueLevel = apps.get_model('Alt', 'AltrueLevel')
    defaults = [
        (0, 'Level 0', 0, 499),
        (1, 'Level 1', 500, 2499),
        (2, 'Level 2', 2500, 9999),
        (3, 'Level 3', 10000, 39999),
        (4, 'Level 4', 40000, 999999),
    ]
    for number, name, min_pts, max_pts in defaults:
        AltrueLevel.objects.get_or_create(
            level_number=number,
            defaults={'name': name, 'minimum_points': min_pts, 'maximum_points': max_pts},
        )


def unseed(apps, schema_editor):
    pass  # no destructive rollback for bootstrap data


class Migration(migrations.Migration):

    dependencies = [
        ('Alt', '0185_companymatchcampaign_companyreward_companyrewardcode_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_default_levels, unseed),
    ]
