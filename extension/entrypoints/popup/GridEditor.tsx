import { useRef } from 'react';
import type { KeyboardEvent } from 'react';
import type { Cell } from '@/lib/model/puzzle';

interface Props {
  cells: Cell[][];
  /** Solved grid to overlay, or null while editing. */
  solution: Cell[][] | null;
  selected: [number, number] | null;
  onSelect: (row: number, col: number) => void;
  onKeyDown: (e: KeyboardEvent<HTMLDivElement>) => void;
}

/**
 * A focusable crossword grid. Click selects a cell; the parent handles keys
 * (letters, Space = toggle block, Backspace = clear, arrows = move).
 */
export function GridEditor({ cells, solution, selected, onSelect, onKeyDown }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div className="grid" tabIndex={0} ref={ref} onKeyDown={onKeyDown}>
      {cells.map((row, r) => (
        // eslint-disable-next-line react/no-array-index-key
        <div className="grid-row" key={r}>
          {row.map((cell, c) => {
            const block = cell === null;
            const given = typeof cell === 'string' && cell !== '';
            const solved = !given && !block ? solution?.[r]?.[c] ?? '' : '';
            const isSelected = selected?.[0] === r && selected?.[1] === c;
            const className = [
              'cell',
              block && 'cell-block',
              given && 'cell-given',
              solved && 'cell-solved',
              isSelected && 'cell-selected',
            ]
              .filter(Boolean)
              .join(' ');

            return (
              <div
                // eslint-disable-next-line react/no-array-index-key
                key={c}
                className={className}
                onMouseDown={(e) => {
                  e.preventDefault(); // keep focus on the grid for key handling
                  onSelect(r, c);
                  ref.current?.focus();
                }}
              >
                {block ? '' : given ? cell : solved}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
