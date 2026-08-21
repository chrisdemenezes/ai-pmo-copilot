import { ChartCard } from "@/components/analytics/chart-card";
import { cn } from "@/lib/utils";
import { computeHealthDistribution, type HealthStatus } from "@/lib/domain/health-distribution";

const STATUS_LABEL: Record<string, string> = {
  green: "Saudável",
  yellow: "Atenção",
  red: "Crítico",
  null: "Sem dado",
};

const STATUS_CLASS: Record<string, string> = {
  green: "bg-ok",
  yellow: "bg-warn",
  red: "bg-danger",
  null: "bg-status-neutral",
};

function key(status: HealthStatus): string {
  return status ?? "null";
}

/**
 * Wave 8 (Executive Analytics), Visual Analytics Section 7.C -- Portfolio
 * Health distribution: how many Projects fall into each real health_status
 * bucket, reusing the exact same taxonomy/labels the Badge component
 * already uses (`healthStatusLabel`), never a second color vocabulary.
 */
export function HealthDistributionChart({ statuses }: { statuses: HealthStatus[] }) {
  const buckets = computeHealthDistribution(statuses);
  const total = statuses.length;
  const isEmpty = total === 0;

  return (
    <ChartCard
      title="Distribuição de Saúde do Portfólio"
      isEmpty={isEmpty}
      emptyMessage="Nenhum projeto para distribuir."
    >
      <div className="flex h-4 overflow-hidden rounded-full">
        {buckets.map((bucket) =>
          bucket.count === 0 ? null : (
            <div
              key={key(bucket.status)}
              className={cn(STATUS_CLASS[key(bucket.status)])}
              style={{ width: `${(bucket.count / total) * 100}%` }}
              title={`${STATUS_LABEL[key(bucket.status)]}: ${bucket.count}`}
            />
          ),
        )}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
        {buckets.map((bucket) => (
          <li key={key(bucket.status)} className="flex items-center gap-1.5">
            <span className={cn("size-2 rounded-full", STATUS_CLASS[key(bucket.status)])} />
            {STATUS_LABEL[key(bucket.status)]}: {bucket.count}
          </li>
        ))}
      </ul>
    </ChartCard>
  );
}
