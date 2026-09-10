import { useState, useEffect } from "react";
import Card from "../common/Card";
import Loading from "../common/Loading";

function ApprovalCenter() {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadApprovals();
  }, []);

  const loadApprovals = async () => {
    try {
      // Placeholder for approval loading
      setApprovals([]);
    } catch (err) {
      console.error("Failed to load approvals:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Approval Center">
      {approvals.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No pending approvals</p>
      ) : (
        <div className="space-y-2">
          {approvals.map((approval) => (
            <div key={approval.id} className="p-3 border rounded-lg">
              <p className="font-medium">{approval.action}</p>
              <p className="text-sm text-gray-500">{approval.description}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default ApprovalCenter;
