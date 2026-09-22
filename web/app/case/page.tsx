"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

/** Old links pointed at /case/?id=; the review screen now shows the case in place. */
function Redirect() {
  const router = useRouter();
  const id = useSearchParams().get("id");
  useEffect(() => {
    router.replace(id ? `/?id=${encodeURIComponent(id)}` : "/");
  }, [id, router]);
  return <p className="paper-empty">Opening the review screen…</p>;
}

export default function CasePage() {
  return (
    <Suspense fallback={null}>
      <Redirect />
    </Suspense>
  );
}
