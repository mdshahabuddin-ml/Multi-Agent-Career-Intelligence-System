import {
  createContext,
  useContext,
  useState,
} from "react";

const ProfileContext =
  createContext(null);


export function ProfileProvider({
  children,
}) {
  const [profile, setProfile] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState(null);


  const value = {
    profile,
    setProfile,
    loading,
    setLoading,
    error,
    setError,
  };


  return (
    <ProfileContext.Provider
      value={value}
    >
      {children}
    </ProfileContext.Provider>
  );
}


export function useProfileContext() {
  const context =
    useContext(ProfileContext);

  if (!context) {
    throw new Error(
      "useProfileContext must be used inside ProfileProvider"
    );
  }

  return context;
}