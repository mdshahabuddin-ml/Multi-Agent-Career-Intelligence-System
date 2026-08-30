import AppLayout from "../components/common/AppLayout";

function Jobs() {
  return (
    <AppLayout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Job Opportunities</h1>
          <p className="text-gray-600 mt-1">Discover and match with relevant job opportunities</p>
        </div>
        <div className="text-center py-12">
          <p className="text-gray-500">Job Search - Coming Soon</p>
        </div>
      </div>
    </AppLayout>
  );
}

export default Jobs;