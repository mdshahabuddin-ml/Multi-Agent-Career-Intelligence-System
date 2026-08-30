import Card from "../components/common/Card";


function Profile() {
  return (
    <div className="page">

      <div className="page-header">
        <h1>Candidate Profile</h1>

        <p>
          Manage your professional
          career profile.
        </p>
      </div>


      <Card title="Professional Profile">

        <div className="form-grid">

          <label>
            Headline

            <input
              type="text"
              placeholder="AI/ML Developer"
            />
          </label>


          <label>
            Target Role

            <input
              type="text"
              placeholder="Machine Learning Engineer"
            />
          </label>


          <label>
            Location

            <input
              type="text"
              placeholder="India"
            />
          </label>


          <label>
            Years of Experience

            <input
              type="number"
              min="0"
              placeholder="0"
            />
          </label>

        </div>


        <label>
          Professional Summary

          <textarea
            rows="6"
            placeholder="Describe your professional background..."
          />
        </label>

      </Card>


      <Card title="Skills">
        <p>
          Skills extracted from your
          resume will appear here.
        </p>
      </Card>


      <Card title="Projects">
        <p>
          Your projects will appear here.
        </p>
      </Card>


      <Card title="Experience">
        <p>
          Your experience will appear here.
        </p>
      </Card>

    </div>
  );
}


export default Profile;