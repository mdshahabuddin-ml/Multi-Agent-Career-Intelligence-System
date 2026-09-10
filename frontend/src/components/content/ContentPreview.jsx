import Card from "../common/Card";

function ContentPreview({ content }) {
  if (!content) {
    return (
      <Card title="Content Preview">
        <p className="text-gray-500 text-center py-4">No content to preview</p>
      </Card>
    );
  }

  return (
    <Card title="Content Preview">
      <div className="space-y-4">
        <h3 className="text-lg font-medium">{content.title}</h3>
        <div className="prose prose-sm max-w-none">
          {content.body}
        </div>
        <div className="flex gap-2">
          <span className="px-2 py-1 text-xs bg-gray-100 rounded">{content.content_type}</span>
          <span className="px-2 py-1 text-xs bg-gray-100 rounded">{content.status}</span>
        </div>
      </div>
    </Card>
  );
}

export default ContentPreview;
