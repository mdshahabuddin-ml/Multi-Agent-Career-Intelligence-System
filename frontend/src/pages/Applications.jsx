import AppLayout from "../components/common/AppLayout";

function Applications() {
  return (
    <AppLayout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
          <p className="text-gray-600 mt-1">Track and manage your job applications</p>
        </div>
        <div className="text-center py-12">
          <p className="text-gray-500">Application Tracker - Coming Soon</p>
        </div>
      </div>
    </AppLayout>
  );
}

export default Applications;