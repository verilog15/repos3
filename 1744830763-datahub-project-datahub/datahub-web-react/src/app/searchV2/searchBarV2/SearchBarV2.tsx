import { CloseCircleFilled, SearchOutlined } from '@ant-design/icons';
import { colors, radius, spacing, transition } from '@src/alchemy-components';
import { AutoComplete } from '@src/alchemy-components/components/AutoComplete';
import { Input, Skeleton } from 'antd';
import { debounce } from 'lodash';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useHistory } from 'react-router';
import styled from 'styled-components/macro';
import analytics, { Event, EventType } from '../../analytics';
import { ANTD_GRAY_V2 } from '../../entity/shared/constants';
import { getEntityPath } from '../../entity/shared/containers/profile/utils';
import { REDESIGN_COLORS } from '../../entityV2/shared/constants';
import { ViewSelect } from '../../entityV2/view/select/ViewSelect';
import { V2_SEARCH_BAR_VIEWS } from '../../onboarding/configV2/HomePageOnboardingConfig';
import { useAppConfig, useIsShowSeparateSiblingsEnabled } from '../../useAppConfig';
import { CommandK } from '../CommandK';
import useAppliedFilters from '../filtersV2/context/useAppliedFilters';
import filterSearchQuery from '../utils/filterSearchQuery';
import AutocompleteFooter from './components/AutocompleteFooter';
import AutocompletePlaceholder from './components/AutocompletePlaceholder';
import Filters from './components/Filters';
import {
    AUTOCOMPLETE_DROPDOWN_ALIGN_WITH_NEW_NAV_BAR,
    DEBOUNCE_ON_SEARCH_TIMEOUT_MS,
    EXACT_AUTOCOMPLETE_OPTION_TYPE,
    RELEVANCE_QUERY_OPTION_TYPE,
} from './constants';
import useAutocompleteSuggestionsOptions from './hooks/useAutocompleteSuggestionsOptions';
import useFocusElementByCommandK from './hooks/useFocusSearchBarByCommandK';
import useRecentlySearchedQueriesOptions from './hooks/useRecentlySearchedQueriesOptions';
import useRecentlyViewedEntitiesOptions from './hooks/useRecentlyViewedEntitiesOptions';
import useViewAllResultsOptions from './hooks/useViewAllResultsOptions';
import { SearchBarProps } from '../SearchBar';

const BOX_SHADOW = `0px -3px 12px 0px rgba(236, 240, 248, 0.5) inset,
0px 3px 12px 0px rgba(255, 255, 255, 0.5) inset,
0px 20px 60px 0px rgba(0, 0, 0, 0.12)`;

const StyledAutoComplete = styled(AutoComplete)<{ $isShowNavBarRedesign?: boolean }>`
    width: 100%;
    max-width: ${(props) => (props.$isShowNavBarRedesign ? '632px' : '540px')};
`;

const SkeletonContainer = styled.div`
    height: 40px;
    width: 100%;
    max-width: 620px;
`;

const SkeletonButton = styled(Skeleton.Button)`
    &&& {
        height: inherit;
        width: inherit;
    }
`;

const AutoCompleteContainer = styled.div<{ viewsEnabled?: boolean; $isShowNavBarRedesign?: boolean }>`
    padding: 0 30px;
    align-items: center;
    border: ${(props) => (props.$isShowNavBarRedesign ? `2px solid ${colors.gray[100]}` : '2px solid transparent')};
    ${(props) => props.$isShowNavBarRedesign && 'box-shadow: 0px 1px 2px 0px rgba(33, 23, 95, 0.07)'};

    transition: border-color 0.3s ease;

    ${(props) =>
        props.viewsEnabled &&
        `
        border-radius: 8px;
        &:focus-within {
            border-color: ${props.$isShowNavBarRedesign ? colors.violet[300] : props.theme.styles['primary-color']};
        }
    `}
`;

export const Wrapper = styled.div<{ $open?: boolean; $isShowNavBarRedesign?: boolean }>`
    background: transparent;

    ${(props) =>
        props.$isShowNavBarRedesign &&
        `
        padding: ${radius.md};
        transition: all ${transition.easing['ease-in']} ${transition.duration.slow};
        border-radius: ${radius.lg} ${radius.lg} ${radius.none} ${radius.none};
    `}

    ${(props) =>
        props.$open &&
        props.$isShowNavBarRedesign &&
        `
        background: ${colors.gray[1500]};
        box-shadow: ${BOX_SHADOW};
    `}
`;

const StyledSearchBar = styled(Input)<{
    $textColor?: string;
    $placeholderColor?: string;
    viewsEnabled?: boolean;
    $isShowNavBarRedesign?: boolean;
}>`
    &&& {
        border-radius: 8px;
        height: 40px;
        font-size: 14px;
        color: #dcdcdc;
        background-color: ${ANTD_GRAY_V2[2]};
        border: 2px solid transparent;
        padding-right: 2.5px;
        ${(props) =>
            !props.viewsEnabled &&
            `
        &:focus-within {
            border-color: ${props.theme.styles['primary-color']};
        }`}

        ${(props) => props.$isShowNavBarRedesign && 'width: 592px;'}
    }

    > .ant-input::placeholder {
        color: ${(props) =>
            props.$placeholderColor || (props.$isShowNavBarRedesign ? REDESIGN_COLORS.GREY_300 : '#dcdcdc')};
    }

    > .ant-input {
        color: ${(props) => props.$textColor || (props.$isShowNavBarRedesign ? '#000' : '#fff')};
    }

    .ant-input-clear-icon {
        height: 15px;
        width: 15px;
    }
`;

const ClearIcon = styled(CloseCircleFilled)`
    svg {
        height: 15px;
        width: 15px;
    }
`;

const ViewSelectContainer = styled.div`
    color: #fff;
    line-height: 20px;
    padding-right: 5.6px;

    &&& {
        border-left: 0px solid ${ANTD_GRAY_V2[5]};
    }
`;

const SearchIcon = styled(SearchOutlined)<{ $isShowNavBarRedesign?: boolean }>`
    color: ${(props) => (props.$isShowNavBarRedesign ? colors.gray[1800] : '#dcdcdc')};
    ${(props) =>
        props.$isShowNavBarRedesign &&
        `
        && svg {
            width: 16px;
            height: 16px;
        }
    `}
`;

const DropdownContainer = styled.div`
    overflow: auto;
    box-shadow: ${BOX_SHADOW};
    border-radius: ${radius.lg};
    background: ${colors.white};
`;

/**
 * Represents the search bar appearing in the default header view.
 */
export const SearchBarV2 = ({
    id,
    isLoading,
    initialQuery,
    placeholderText,
    suggestions,
    isSuggestionsLoading,
    onSearch,
    onQueryChange,
    onFilter,
    entityRegistry,
    style,
    inputStyle,
    autoCompleteStyle,
    fixAutoComplete,
    showCommandK = false,
    viewsEnabled = false,
    combineSiblings = false,
    onFocus,
    onBlur,
    showViewAllResults = false,
    textColor,
    placeholderColor,
    isShowNavBarRedesign,
}: SearchBarProps) => {
    const history = useHistory();
    const appConfig = useAppConfig();
    const showAutoCompleteResults = appConfig?.config?.featureFlags?.showAutoCompleteResults;
    const isShowSeparateSiblingsEnabled = useIsShowSeparateSiblingsEnabled();
    const finalCombineSiblings = isShowSeparateSiblingsEnabled ? false : combineSiblings;

    const [searchQuery, setSearchQuery] = useState<string>(initialQuery || '');
    const [isDropdownVisible, setIsDropdownVisible] = useState(false);
    // used to show Loader when we searching for suggestions in both cases for the first time and after clearing searchQuery
    const [isSuggestionsInitialized, setIsSuggestionsInitialized] = useState<boolean>(false);
    const [isSearchBarFocused, setIsFocused] = useState(false);
    const { appliedFilters, hasAppliedFilters, flatAppliedFilters, clear, updateFieldFilters } = useAppliedFilters();

    const searchInputRef = useRef(null);
    useFocusElementByCommandK(searchInputRef, !showCommandK);

    useEffect(() => onFilter?.(appliedFilters), [appliedFilters, onFilter]);

    useEffect(() => {
        if (searchQuery === '') setIsSuggestionsInitialized(false);
    }, [searchQuery]);

    useEffect(() => {
        if (!isSuggestionsLoading) setIsSuggestionsInitialized(true);
    }, [isSuggestionsLoading]);

    const recentlySearchedQueriesOptions = useRecentlySearchedQueriesOptions();
    const recentlyViewedEntitiesOptions = useRecentlyViewedEntitiesOptions();

    const initialOptions = useMemo(() => {
        return [...recentlyViewedEntitiesOptions, ...recentlySearchedQueriesOptions];
    }, [recentlyViewedEntitiesOptions, recentlySearchedQueriesOptions]);

    const viewAllResultsOptions = useViewAllResultsOptions(searchQuery, showViewAllResults);

    const isSearching = useMemo(() => {
        const hasSearchQuery = searchQuery !== '';
        return hasSearchQuery || hasAppliedFilters;
    }, [searchQuery, hasAppliedFilters]);

    const hasAutocompleteResults = useMemo(() => suggestions.length > 0, [suggestions.length]);

    const autocompleteSuggestionsOptions = useAutocompleteSuggestionsOptions(
        suggestions,
        searchQuery,
        isSuggestionsLoading,
        isSuggestionsInitialized,
        finalCombineSiblings,
    );

    const options = useMemo(() => {
        if (!isSearching) return initialOptions;

        if (showAutoCompleteResults) {
            if (!isSuggestionsLoading && !hasAutocompleteResults) return [];
            return [...viewAllResultsOptions, ...autocompleteSuggestionsOptions];
        }

        return [];
    }, [
        isSearching,
        hasAutocompleteResults,
        initialOptions,
        autocompleteSuggestionsOptions,
        viewAllResultsOptions,
        showAutoCompleteResults,
        isSuggestionsLoading,
    ]);

    const searchBarWrapperRef = useRef<HTMLDivElement>(null);

    const onFocusHandler = useCallback(() => {
        setIsFocused(true);
        onFocus?.();
    }, [onFocus]);

    const onBlurHandler = useCallback(() => {
        setIsFocused(false);
        onBlur?.();
    }, [onBlur]);

    const onChangeHandler = (value: string) => {
        setSearchQuery(filterSearchQuery(value));
    };

    const onClearHandler = useCallback(() => {
        setSearchQuery('');
        clear();
    }, [clear]);

    // clear filters when this search bar is unmounted (ie. going from search results to home page)
    useEffect(() => () => onClearHandler(), [onClearHandler]);

    const onSearchHandler = showAutoCompleteResults
        ? debounce((query: string) => onQueryChange?.(query), DEBOUNCE_ON_SEARCH_TIMEOUT_MS)
        : undefined;

    const runSearching = useCallback(() => {
        const filteredSearchQuery = filterSearchQuery(searchQuery || '');
        let cleanedQuery = filteredSearchQuery.trim();
        if (cleanedQuery.length === 0) {
            cleanedQuery = '*';
        } else if (!cleanedQuery.includes('*') && cleanedQuery.length < 3) {
            cleanedQuery = `${cleanedQuery}*`;
        }

        onSearch(filteredSearchQuery, flatAppliedFilters);
        setIsDropdownVisible(false);
    }, [searchQuery, flatAppliedFilters, onSearch]);

    const onSelectHandler = useCallback(
        (value, option) => {
            // If the autocomplete option type is NOT an entity, then render as a normal search query.
            if (option.type === EXACT_AUTOCOMPLETE_OPTION_TYPE || option.type === RELEVANCE_QUERY_OPTION_TYPE) {
                onSearch(`${filterSearchQuery(value as string)}`, flatAppliedFilters);
                analytics.event({
                    type: EventType.SelectAutoCompleteOption,
                    optionType: option.type,
                } as Event);
            } else {
                // Navigate directly to the entity profile.
                history.push(getEntityPath(option.type, value, entityRegistry, false, false));
                onClearHandler();
                analytics.event({
                    type: EventType.SelectAutoCompleteOption,
                    optionType: option.type,
                    entityType: option.type,
                    entityUrn: value,
                } as Event);
            }
            setIsDropdownVisible(false);
        },
        [onSearch, onClearHandler, entityRegistry, flatAppliedFilters, history],
    );

    const viewsEnabledStyle = {
        ...style,
        backgroundColor: inputStyle?.backgroundColor,
    };

    const onDropdownVisibilityChange = useCallback((isOpen) => {
        if (!isOpen) {
            setIsDropdownVisible(isOpen);
        } else {
            // set timeout so that we allow search bar to grow in width and therefore allow autocomplete to grow
            setTimeout(() => {
                setIsDropdownVisible(isOpen);
            }, 0);
        }
    }, []);

    const onSearchBarValueChanged = useCallback(
        (value: string) => {
            setSearchQuery(value);
            if (value === '') clear();
        },
        [clear],
    );

    const onClearFilters = useCallback(() => clear(), [clear]);

    return (
        <>
            {isLoading ? (
                <SkeletonContainer>
                    <SkeletonButton shape="square" active block />
                </SkeletonContainer>
            ) : (
                <Wrapper $open={isDropdownVisible} $isShowNavBarRedesign={isShowNavBarRedesign}>
                    <AutoCompleteContainer
                        viewsEnabled={viewsEnabled}
                        $isShowNavBarRedesign={isShowNavBarRedesign}
                        id={id}
                        style={viewsEnabled ? viewsEnabledStyle : style}
                        ref={searchBarWrapperRef}
                    >
                        <StyledAutoComplete
                            dataTestId="search-bar"
                            $isShowNavBarRedesign={isShowNavBarRedesign}
                            defaultActiveFirstOption={false}
                            style={autoCompleteStyle}
                            options={options}
                            filterOption={false}
                            dropdownRender={(props) => {
                                return (
                                    <DropdownContainer>
                                        {isSearching && (
                                            <Filters
                                                query={searchQuery ?? ''}
                                                appliedFilters={appliedFilters}
                                                updateFieldAppliedFilters={updateFieldFilters}
                                            />
                                        )}
                                        {props}
                                        <AutocompleteFooter isSomethingSelected={!!searchQuery} />
                                    </DropdownContainer>
                                );
                            }}
                            notFoundContent={
                                <AutocompletePlaceholder
                                    hasAppliedFilters={hasAppliedFilters}
                                    isSearching={isSearching}
                                    onClearFilters={onClearFilters}
                                />
                            }
                            onSelect={onSelectHandler}
                            onSearch={onSearchHandler}
                            defaultValue={initialQuery || undefined}
                            value={searchQuery}
                            onChange={onChangeHandler}
                            dropdownAlign={
                                isShowNavBarRedesign ? AUTOCOMPLETE_DROPDOWN_ALIGN_WITH_NEW_NAV_BAR : undefined
                            }
                            onClear={onClearHandler}
                            dropdownStyle={{
                                maxHeight: 1000,
                                overflowY: 'visible',
                                position: (fixAutoComplete && 'fixed') || 'relative',
                                backgroundColor: colors.gray[1500],
                                boxShadow: BOX_SHADOW,
                                ...(isShowNavBarRedesign
                                    ? {
                                          padding: spacing.xsm,
                                          borderRadius: `${radius.none} ${radius.none} ${radius.lg} ${radius.lg}`,
                                      }
                                    : {}),
                            }}
                            onDropdownVisibleChange={onDropdownVisibilityChange}
                            open={isDropdownVisible}
                            dropdownContentHeight={480}
                            dropdownMatchSelectWidth={isShowNavBarRedesign ? 664 : true}
                        >
                            <StyledSearchBar
                                bordered={false}
                                placeholder={placeholderText}
                                onPressEnter={() => runSearching()}
                                style={{ ...inputStyle, color: '#fff' }}
                                value={searchQuery}
                                onChange={(e) => onSearchBarValueChanged(e.target.value)}
                                data-testid="search-input"
                                onFocus={onFocusHandler}
                                onBlur={onBlurHandler}
                                viewsEnabled={viewsEnabled}
                                $isShowNavBarRedesign={isShowNavBarRedesign}
                                allowClear={
                                    ((isDropdownVisible || isSearchBarFocused) && { clearIcon: <ClearIcon /> }) || false
                                }
                                prefix={
                                    <>
                                        <SearchIcon
                                            $isShowNavBarRedesign={isShowNavBarRedesign}
                                            onClick={() => runSearching()}
                                        />
                                    </>
                                }
                                ref={searchInputRef}
                                suffix={
                                    <>
                                        {(showCommandK && !isDropdownVisible && !isSearchBarFocused && <CommandK />) ||
                                            null}
                                    </>
                                }
                                $textColor={textColor}
                                $placeholderColor={placeholderColor}
                                width={isShowNavBarRedesign ? '592px' : '100%'}
                            />
                        </StyledAutoComplete>
                        {viewsEnabled && (
                            <ViewSelectContainer id={V2_SEARCH_BAR_VIEWS}>
                                <ViewSelect />
                            </ViewSelectContainer>
                        )}
                    </AutoCompleteContainer>
                </Wrapper>
            )}
        </>
    );
};
