import HermesDashboard from "../components/hermes/HermesDashboard";
import HermesChat from "../components/hermes/HermesChat";

function Hermes() {
  return (
    <div className="space-y-6">
      <HermesDashboard />
      <HermesChat />
    </div>
  );
}

export default Hermes;
