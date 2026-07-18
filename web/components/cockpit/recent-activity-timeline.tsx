import { Card, CardContent } from "@/components/ui/card";
import type { ActivityEvent } from "@/lib/mock/cockpit-data";

/** Entrega 2.4 -- Recent Activity (dados simulados). */
export function RecentActivityTimeline({ events }: { events: ActivityEvent[] }) {
  const grouped = events.reduce<Record<string, ActivityEvent[]>>((acc, event) => {
    (acc[event.day] ??= []).push(event);
    return acc;
  }, {});

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-5">
        {Object.entries(grouped).map(([day, dayEvents]) => (
          <div key={day}>
            <p className="font-mono text-xs font-semibold uppercase tracking-wide text-ink-muted">
              {day}
            </p>
            <ul className="mt-2 flex flex-col gap-1.5">
              {dayEvents.map((event) => (
                <li key={event.description} className="flex items-start gap-2 text-sm text-ink">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                  {event.description}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
