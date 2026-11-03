import { Component, type ReactNode } from "react";
import { OctagonAlert } from "lucide-react";
import { Empty } from "./ui/Feedback";

// Keeps one broken screen from blanking the whole app.
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="page">
        <Empty icon={<OctagonAlert size={18} />} title="This screen hit an error"
          action={<button className="btn" onClick={() => this.setState({ error: null })}>Try again</button>}>
          <span className="mono" style={{ fontSize: 12 }}>{this.state.error.message}</span>
        </Empty>
      </div>
    );
  }
}
