export function Table({
  headers,
  rows,
}: Readonly<{ headers: string[]; rows: React.ReactNode[][] }>) {
  return (
    <div className="overflow-hidden rounded-[20px] border border-stone-200">
      <table className="min-w-full divide-y divide-stone-200 bg-white text-sm">
        <thead className="bg-stone-50">
          <tr>
            {headers.map((header) => (
              <th key={header} className="px-4 py-3 text-start font-semibold text-stone-700">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="px-4 py-3 align-top text-stone-800">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
