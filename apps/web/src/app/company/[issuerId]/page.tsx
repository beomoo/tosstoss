import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CompanyOverview } from "@/components/CompanyOverview";
import { BackendRequestError, getCompanyOverview } from "@/lib/api.server";

export const metadata: Metadata = { title: "Company" };

interface CompanyPageProps {
  params: Promise<{ issuerId: string }>;
}

export default async function CompanyPage({ params }: CompanyPageProps) {
  const { issuerId } = await params;
  let response: Awaited<ReturnType<typeof getCompanyOverview>>;

  try {
    response = await getCompanyOverview(issuerId);
  } catch (error) {
    if (error instanceof BackendRequestError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return <CompanyOverview overview={response.data} />;
}
