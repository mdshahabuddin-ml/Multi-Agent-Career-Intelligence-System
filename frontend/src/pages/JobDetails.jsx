import AppLayout from "../components/common/AppLayout";

function JobDetails() {
  return (
    <AppLayout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Job Details</h1>
          <p className="text-gray-600 mt-1">View detailed job information and match analysis</p>
        </div>
        <div className="text-center py-12">
          <p className="text-gray-500">Job Details - Coming Soon</p>
        </div>
      </div>
    </AppLayout>
  );
}

export default JobDetails;