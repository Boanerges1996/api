import datetime

from django.core.management.base import BaseCommand

from app.models.conference import Conference


class Command(BaseCommand):
    help = 'Close conferences stuck as ongoing for longer than the specified hours'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=4,
            help='Close conferences ongoing for longer than this many hours (default: 4)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be closed without making changes',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

        stale = Conference.objects.filter(ongoing=True, created_at__lt=cutoff)
        count = stale.count()

        if count == 0:
            self.stdout.write('No stale conferences found.')
            return

        self.stdout.write(f'Found {count} conferences ongoing for more than {hours} hours.')

        now = datetime.datetime.utcnow()

        for conference in stale:
            age = now - conference.created_at
            self.stdout.write(f'  {conference.id} ({conference.conference_name or conference.conference_id}) - ongoing for {age}')

            if not dry_run:
                for connection in conference.connections.filter(end_time__isnull=True):
                    connection.end(now)
                    connection.save()

                for session in conference.sessions.filter(end_time__isnull=True):
                    session.should_stop_call(now)
                    session.save()

                conference.should_stop_call(now)
                conference.save()

        if dry_run:
            self.stdout.write(f'\nDry run - no changes made. Run without --dry-run to close these conferences.')
        else:
            self.stdout.write(f'\nClosed {count} stale conferences.')
