import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

const COLUMNS = [
  'Serial Number',
  'EPIC Number',
  'Name',
  'Relative Name',
  'Relation Type',
  'House Number',
  'Age',
  'Gender',
];

const FIELD_KEYS = [
  'serial_number',
  'epic_number',
  'name',
  'relative_name',
  'relation_type',
  'house_number',
  'age',
  'gender',
];

export default function VoterTable({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <p className="text-sm text-slate-400">No preview data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <ScrollArea className="w-full">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50/80">
              {COLUMNS.map((col) => (
                <TableHead
                  key={col}
                  className="text-xs font-semibold uppercase tracking-wider whitespace-nowrap py-3.5 px-4"
                  style={{ color: '#1a3c6e' }}
                >
                  {col}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row, i) => (
              <TableRow
                key={i}
                className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50/40'}
              >
                {FIELD_KEYS.map((key) => (
                  <TableCell key={key} className="text-sm text-slate-700 whitespace-nowrap py-3 px-4">
                    {row[key] || '—'}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </div>
  );
}