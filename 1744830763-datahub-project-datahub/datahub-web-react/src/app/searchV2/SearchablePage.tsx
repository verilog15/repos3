import { REDESIGN_COLORS } from '@app/entityV2/shared/constants';
import React, { useCallback, useEffect, useState } from 'react';
import { useHistory, useLocation } from 'react-router';
import { debounce } from 'lodash';
import * as QueryString from 'query-string';
import styled, { useTheme } from 'styled-components';
import { colors } from '@src/alchemy-components';
import { useDebounce } from 'react-use';
import { SearchHeader } from './SearchHeader';
import { useEntityRegistry } from '../useEntityRegistry';
import { FacetFilterInput } from '../../types.generated';
import {
    GetAutoCompleteMultipleResultsQuery,
    useGetAutoCompleteMultipleResultsLazyQuery,
} from '../../graphql/search.generated';
import { navigateToSearchUrl } from './utils/navigateToSearchUrl';
import analytics, { EventType } from '../analytics';
import useFilters from './utils/useFilters';
import { PageRoutes } from '../../conf/Global';
import { getAutoCompleteInputFromQuickFilter } from './utils/filterUtils';
import { useQuickFiltersContext } from '../../providers/QuickFiltersContext';
import { useUserContext } from '../context/useUserContext';
import { useSelectedSortOption } from '../search/context/SearchContext';
import { NavSidebar as NavSidebarRedesign } from '../homeV2/layout/navBarRedesign/NavSidebar';
import { NavSidebar } from '../homeV2/layout/NavSidebar';
import { useShowNavBarRedesign } from '../useShowNavBarRedesign';
import { FieldToAppliedFieldFiltersMap } from './filtersV2/types';
import { generateOrFilters } from './utils/generateOrFilters';
import { UnionType } from './utils/constants';
import { useAppConfig } from '../useAppConfig';
import { convertFiltersMapToFilters } from './filtersV2/utils';

const Body = styled.div`
    display: flex;
    flex-direction: row;
    flex: 1;
`;

const BodyBackground = styled.div<{ $isShowNavBarRedesign?: boolean }>`
    background-color: ${(props) => (props.$isShowNavBarRedesign ? colors.gray[1600] : REDESIGN_COLORS.BACKGROUND)};
    position: fixed;
    height: 100%;
    width: 100%;
    z-index: -2;
`;

const Navigation = styled.div<{ $isShowNavBarRedesign?: boolean }>`
    z-index: ${(props) => (props.$isShowNavBarRedesign ? 0 : 200)};
`;

const Content = styled.div<{ $isShowNavBarRedesign?: boolean }>`
    border-radius: ${(props) =>
        props.$isShowNavBarRedesign ? props.theme.styles['border-radius-navbar-redesign'] : '8px'};
    margin-top: ${(props) => (props.$isShowNavBarRedesign ? '56px' : '72px')};
    ${(props) =>
        props.$isShowNavBarRedesign &&
        `
        padding: 11px 15px 11px 3px;
    `}
    flex: 1;
    display: flex;
    flex-direction: column;
    max-height: ${(props) => (props.$isShowNavBarRedesign ? 'calc(100vh - 56px)' : 'calc(100vh - 72px)')};
    width: 100%;
    overflow: ${(props) => (props.$isShowNavBarRedesign ? 'hidden' : 'auto')};
`;

const FIFTH_SECOND_IN_MS = 100;

type Props = React.PropsWithChildren<any>;

const isSearchResultPage = (path: string) => {
    return path.startsWith(PageRoutes.SEARCH);
};

/**
 * A page that includes a sticky search header (nav bar)
 */
export const SearchablePage = ({ children }: Props) => {
    const location = useLocation();
    const appConfig = useAppConfig();
    const showSearchBarAutocompleteRedesign = appConfig.config.featureFlags?.showSearchBarAutocompleteRedesign;

    const params = QueryString.parse(location.search, { arrayFormat: 'comma' });
    const paramFilters: Array<FacetFilterInput> = useFilters(params);
    const filters = isSearchResultPage(location.pathname) ? paramFilters : [];
    const currentQuery: string = isSearchResultPage(location.pathname)
        ? decodeURIComponent(params.query ? (params.query as string) : '')
        : '';
    const selectedSortOption = useSelectedSortOption();
    const isShowNavBarRedesign = useShowNavBarRedesign();

    const history = useHistory();
    const entityRegistry = useEntityRegistry();
    const themeConfig = useTheme();
    const { selectedQuickFilter } = useQuickFiltersContext();

    const [getAutoCompleteResults, { data: suggestionsData, loading: isSuggestionsLoading }] =
        useGetAutoCompleteMultipleResultsLazyQuery();
    const userContext = useUserContext();
    const [newSuggestionData, setNewSuggestionData] = useState<GetAutoCompleteMultipleResultsQuery | undefined>();
    const viewUrn = userContext.localState?.selectedViewUrn;

    const [appliedFilters, setAppliedFilters] = useState<FieldToAppliedFieldFiltersMap | undefined>(new Map());
    const [searchQuery, setSearchQuery] = useState<string>(currentQuery);

    useEffect(() => {
        if (suggestionsData !== undefined) {
            setNewSuggestionData(suggestionsData);
        }
    }, [suggestionsData]);

    const search = (query: string, newFilters?: FacetFilterInput[]) => {
        analytics.event({
            type: EventType.SearchEvent,
            query,
            pageNumber: 1,
            originPath: window.location.pathname,
            selectedQuickFilterTypes: selectedQuickFilter ? [selectedQuickFilter.field] : undefined,
            selectedQuickFilterValues: selectedQuickFilter ? [selectedQuickFilter.value] : undefined,
        });

        const newAppliedFilters = newFilters && newFilters?.length > 0 ? newFilters : filters;

        navigateToSearchUrl({
            query,
            filters: newAppliedFilters,
            history,
            selectedSortOption,
        });
    };

    const autoComplete = debounce((query: string) => {
        if (query && query.trim() !== '') {
            getAutoCompleteResults({
                variables: {
                    input: {
                        query,
                        viewUrn,
                        ...getAutoCompleteInputFromQuickFilter(selectedQuickFilter),
                    },
                },
            });
        }
    }, FIFTH_SECOND_IN_MS);

    const autoCompleteWithFilters = useCallback(
        (query: string, appliedFiltersFprAutocomplete: FieldToAppliedFieldFiltersMap | undefined) => {
            if (query.trim() === '') return null;
            if (!showSearchBarAutocompleteRedesign) return null;

            const convertedFilters = convertFiltersMapToFilters(appliedFiltersFprAutocomplete);
            const orFilters = generateOrFilters(UnionType.AND, convertedFilters);

            getAutoCompleteResults({
                variables: {
                    input: {
                        query,
                        viewUrn,
                        orFilters,
                    },
                },
            });
            return null;
        },
        [getAutoCompleteResults, showSearchBarAutocompleteRedesign, viewUrn],
    );

    useDebounce(() => autoCompleteWithFilters(searchQuery, appliedFilters), FIFTH_SECOND_IN_MS, [
        searchQuery,
        appliedFilters,
        autoCompleteWithFilters,
    ]);

    // Load correct autocomplete results on initial page load.
    useEffect(() => {
        if (currentQuery && currentQuery.trim() !== '') {
            getAutoCompleteResults({
                variables: {
                    input: {
                        query: currentQuery,
                        viewUrn,
                    },
                },
            });
        }
    }, [currentQuery, getAutoCompleteResults, viewUrn]);

    const FinalNavBar = isShowNavBarRedesign ? NavSidebarRedesign : NavSidebar;

    return (
        <>
            <SearchHeader
                initialQuery={currentQuery as string}
                placeholderText={themeConfig.content.search.searchbarMessage}
                suggestions={
                    (newSuggestionData &&
                        newSuggestionData?.autoCompleteForMultiple &&
                        newSuggestionData.autoCompleteForMultiple.suggestions) ||
                    []
                }
                isSuggestionsLoading={isSuggestionsLoading}
                onSearch={search}
                onQueryChange={showSearchBarAutocompleteRedesign ? setSearchQuery : autoComplete}
                entityRegistry={entityRegistry}
                onFilter={(newFilters) => setAppliedFilters(newFilters)}
            />
            <BodyBackground $isShowNavBarRedesign={isShowNavBarRedesign} />
            <Body>
                <Navigation $isShowNavBarRedesign={isShowNavBarRedesign}>
                    <FinalNavBar />
                </Navigation>
                <Content $isShowNavBarRedesign={isShowNavBarRedesign}>{children}</Content>
            </Body>
        </>
    );
};
