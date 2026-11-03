import { redirect } from "next/navigation";
import { getMe, type Me } from "@/lib/api";

/** Page-level gate for a friendly redirect. The API enforces the same roles on every call. */
export async function requireStaff(next: string, roles: string[] = ["editor", "admin"]): Promise<Me> {
  const me = await getMe();
  if (!me) redirect(`/login?next=${encodeURIComponent(next)}`);
  if (!roles.includes(me.role)) redirect(me.role === "donor" ? "/account" : "/admin");
  return me;
}

export const STATUS_LABEL: Record<string, string> = { draft: "Draft", in_review: "In review", published: "Published" };

export const TRANSITIONS: Record<string, { to: string; label: string; roles: string[] }[]> = {
  draft: [{ to: "in_review", label: "Send for review", roles: ["editor", "admin"] }],
  in_review: [
    { to: "published", label: "Publish", roles: ["admin"] },
    { to: "draft", label: "Send back to draft", roles: ["admin"] },
  ],
  published: [{ to: "draft", label: "Unpublish to edit", roles: ["admin"] }],
};
