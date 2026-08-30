import {
    useCallback,
    useState,
} from "react";


export default function useApi(
    apiFunction
) {
    const [data, setData] =
    useState(null);

    const [loading, setLoading] =
    useState(false);

    const [error, setError] =
    useState(null);


    const execute = useCallback(
        async(...args) => {
            setLoading(true);
            setError(null);

            try {
                const result =
                    await apiFunction(...args);

                setData(result);

                return result;
            } catch (err) {
                setError(err);

                throw err;
            } finally {
                setLoading(false);
            }
        }, [apiFunction]
    );


    return {
        data,
        loading,
        error,
        execute,
    };
}