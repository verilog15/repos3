import React from 'react';
import NoResultsFoundPlaceholder from './NoResultsFoundPlaceholder';
import NoSearchingPlaceholder from './NoSearchingPlaceholder';

interface Props {
    isSearching?: boolean;
    hasAppliedFilters?: boolean;
    onClearFilters?: () => void;
}

export default function AutocompletePlaceholder({ isSearching, hasAppliedFilters, onClearFilters }: Props) {
    if (isSearching) {
        return <NoResultsFoundPlaceholder hasAppliedFilters={hasAppliedFilters} onClearFilters={onClearFilters} />;
    }

    return <NoSearchingPlaceholder />;
}
