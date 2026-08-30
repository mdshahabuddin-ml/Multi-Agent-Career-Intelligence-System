import {
  createContext,
  useContext,
  useState,
} from "react";

const AppContext =
  createContext(null);


export function AppProvider({
  children,
}) {
  const [sidebarOpen, setSidebarOpen] =
    useState(true);

  const [notification, setNotification] =
    useState(null);


  const showNotification = (
    message,
    type = "info"
  ) => {
    setNotification({
      message,
      type,
    });
  };


  const clearNotification = () => {
    setNotification(null);
  };


  return (
    <AppContext.Provider
      value={{
        sidebarOpen,
        setSidebarOpen,
        notification,
        showNotification,
        clearNotification,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}


export function useAppContext() {
  const context =
    useContext(AppContext);

  if (!context) {
    throw new Error(
      "useAppContext must be used inside AppProvider"
    );
  }

  return context;
}