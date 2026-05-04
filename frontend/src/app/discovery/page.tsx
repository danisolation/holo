import { DiscoveryTable } from "@/components/discovery-table";

export default function DiscoveryPage() {
  return (
    <div data-testid="discovery-page">
      <h2 className="text-2xl font-bold tracking-tight mb-2">
        Khám phá cổ phiếu
      </h2>
      <DiscoveryTable />
    </div>
  );
}
