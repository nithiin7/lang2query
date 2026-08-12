import { redirect } from "next/navigation";

/** "/" — redirects to the chat UI, which is the app's only real page today. */
export default function RootPage() {
  redirect("/chat");
}
