/**
 * V1 Product & Capability Completion, Pacote J (Founder Decision):
 * visualização alternativa (Board) dos mesmos dados/estados já reais de
 * uma Capability -- nunca um gerenciador de tarefas. Sempre somente
 * leitura: nenhuma coluna aqui representa uma mutação de domínio, então
 * nenhum drag-and-drop é oferecido (regra explícita do mandato --
 * inventar isso sem contrato de domínio seria um estado fictício).
 */
export interface BoardColumn<T> {
  key: string;
  label: string;
  items: T[];
}

export function BoardView<T>({
  columns,
  getItemKey,
  renderItem,
}: {
  columns: BoardColumn<T>[];
  getItemKey: (item: T) => string;
  renderItem: (item: T) => React.ReactNode;
}) {
  return (
    <div className="flex gap-4 overflow-x-auto pb-2" data-testid="board-view">
      {columns.map((column) => (
        <div
          key={column.key}
          className="flex w-72 shrink-0 flex-col gap-3 rounded-lg border border-border bg-surface-2 p-3"
        >
          <div className="flex items-center justify-between px-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
              {column.label}
            </p>
            <span className="font-mono text-xs tabular-nums text-ink-faint">
              {column.items.length}
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {column.items.length === 0 ? (
              <p className="px-1 text-xs text-ink-faint">Nenhum item</p>
            ) : (
              column.items.map((item) => <div key={getItemKey(item)}>{renderItem(item)}</div>)
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
