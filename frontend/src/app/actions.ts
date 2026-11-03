"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

const YEAR = 60 * 60 * 24 * 365;

export async function setLang(formData: FormData) {
  const v = formData.get("lang") === "en" ? "en" : "hi";
  (await cookies()).set("lang", v, { path: "/", maxAge: YEAR, sameSite: "lax" });
  revalidatePath("/", "layout");
}
