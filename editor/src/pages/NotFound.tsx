import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Empty } from "@/components/ui/Feedback";

export function NotFound() {
  return (
    <div className="page"><Empty icon={<Compass size={18} />} title="Nothing here" action={<Link className="btn" to="/">Back to Create</Link>}>
      This page doesn't exist. It may have been a project that was moved or deleted.
    </Empty></div>
  );
}
