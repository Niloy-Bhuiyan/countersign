"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

/** Old links pointed at /case/?id=; invoices now open on the review page. */
function Redirect() {
  const router = useRouter();
  const id = useSearchParams().get("id");
  useEffect(() => {
    router.replace(id ? `/review/?id=${encodeURIComponent(id)}` : "/review/");
  }, [id, router]);
  return <p className="page muted">Opening the invoice…</p>;
}

export default function CasePage() {
  return (
    <Suspense fallback={null}>
      <Redirect />
    </Suspense>
  );
}
