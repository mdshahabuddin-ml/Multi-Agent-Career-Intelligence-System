import Card from "../common/Card";

function ContentApproval({ content, onApprove, onReject }) {
  if (!content) {
    return (
      <Card title="Content Approval">
        <p className="text-gray-500 text-center py-4">No content pending approval</p>
      </Card>
    );
  }

  return (
    <Card title="Content Approval">
      <div className="space-y-4">
        <div>
          <h3 className="font-medium">{content.title}</h3>
          <p className="text-sm text-gray-500 mt-1">{content.body?.substring(0, 200)}...</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onApprove(content.id)}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
          >
            Approve
          </button>
          <button
            onClick={() => onReject(content.id)}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Reject
          </button>
        </div>
      </div>
    </Card>
  );
}

export default ContentApproval;
