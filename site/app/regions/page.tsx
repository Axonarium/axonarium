import type { Metadata } from "next";
import Link from "next/link";

import { DataUnavailable } from "@/components/data-unavailable";
import { RegionList } from "@/components/region-list";
import { getRegionIndex } from "@/lib/data";

export const revalidate = 300;
export const metadata: Metadata = { title: "Regions" };

export default async function Regions() {
  const regions = await getRegionIndex();
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Regions</h1>
        <p className="max-w-2xl text-muted-foreground">
          Every atlas region with a connection, the amygdala&apos;s first. Open one for its inputs and outputs and the
          evidence behind them. Region names and versions come from the{" "}
          <Link href="/atlases" className="underline underline-offset-4">
            atlases
          </Link>
          .
        </p>
      </div>
      {regions === null ? <DataUnavailable /> : <RegionList regions={regions} />}
    </div>
  );
}
