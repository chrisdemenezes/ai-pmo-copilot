import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ActionPriority, PriorityAction } from "@/lib/mock/cockpit-data";

function priorityVariant(priority: ActionPriority) {
  if (priority === "Alta") return "danger" as const;
  if (priority === "Média") return "warn" as const;
  return "neutral" as const;
}

/** Entrega 2.4 -- Actions Center (dados simulados). */
export function ActionsCenterTable({ actions }: { actions: PriorityAction[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Prioridade</TableHead>
            <TableHead>Ação</TableHead>
            <TableHead>Responsável</TableHead>
            <TableHead>Prazo</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {actions.map((item) => (
            <TableRow key={item.action}>
              <TableCell>
                <Badge variant={priorityVariant(item.priority)}>{item.priority}</Badge>
              </TableCell>
              <TableCell className="font-medium text-ink">{item.action}</TableCell>
              <TableCell className="text-ink-muted">{item.owner}</TableCell>
              <TableCell className="text-ink-muted">{item.due}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
