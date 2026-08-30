import { AuthProvider } from "./context/AuthContext";
import { ProfileProvider } from "./context/ProfileContext";
import { AppProvider } from "./context/AppContext";

import AppRoutes from "./routes/AppRoutes";


function App() {
  return (
    <AppProvider>

      <AuthProvider>

        <ProfileProvider>

          <AppRoutes />

        </ProfileProvider>

      </AuthProvider>

    </AppProvider>
  );
}


export default App;