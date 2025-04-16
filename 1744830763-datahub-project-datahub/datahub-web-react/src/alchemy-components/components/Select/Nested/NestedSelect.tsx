import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Dropdown, Icon } from '@components';

import {
    ActionButtonsContainer,
    Container,
    DropdownContainer,
    OptionList,
    SelectBase,
    SelectLabel,
    StyledClearButton,
} from '../components';

import { CustomOptionRenderer, SelectLabelProps, SelectSizeOptions } from '../types';
import { NestedOption } from './NestedOption';
import { NestedSelectOption } from './types';
import DropdownSearchBar from '../private/DropdownSearchBar';
import DropdownFooterActions from '../private/DropdownFooterActions';
import SelectLabelRenderer from '../private/SelectLabelRenderer/SelectLabelRenderer';
import { filterNestedSelectOptions } from './utils';

const NO_PARENT_VALUE = 'no_parent_value';

export interface ActionButtonsProps<OptionType extends NestedSelectOption = NestedSelectOption> {
    fontSize?: SelectSizeOptions;
    selectedOptions: OptionType[];
    isOpen: boolean;
    isDisabled: boolean;
    isReadOnly: boolean;
    handleClearSelection: () => void;
    showClear?: boolean;
}

const SelectActionButtons = <OptionType extends NestedSelectOption = NestedSelectOption>({
    selectedOptions,
    isOpen,
    isDisabled,
    isReadOnly,
    handleClearSelection,
    fontSize = 'md',
    showClear = false,
}: ActionButtonsProps<OptionType>) => {
    return (
        <ActionButtonsContainer>
            {showClear && !!selectedOptions.length && !isDisabled && !isReadOnly && (
                <StyledClearButton
                    icon={{ icon: 'Close', source: 'material', size: 'lg' }}
                    isCircle
                    onClick={handleClearSelection}
                    size={fontSize}
                    data-testid="dropdown-option-clear-icon"
                />
            )}
            <Icon icon="CaretDown" source="phosphor" rotate={isOpen ? '180' : '0'} size="md" color="gray" />
        </ActionButtonsContainer>
    );
};

export interface SelectProps<OptionType extends NestedSelectOption = NestedSelectOption> {
    options: OptionType[];
    label?: string;
    value?: string;
    initialValues?: OptionType[];
    onCancel?: () => void;
    onUpdate?: (selectedValues: OptionType[]) => void;
    size?: SelectSizeOptions;
    showSearch?: boolean;
    isDisabled?: boolean;
    isReadOnly?: boolean;
    isRequired?: boolean;
    isMultiSelect?: boolean;
    areParentsSelectable?: boolean;
    loadData?: (node: OptionType) => void;
    onSearch?: (query: string) => void;
    width?: number | 'full' | 'fit-content';
    height?: number;
    placeholder?: string;
    searchPlaceholder?: string;
    isLoadingParentChildList?: boolean;
    showClear?: boolean;
    shouldAlwaysSyncParentValues?: boolean;
    hideParentCheckbox?: boolean;
    implicitlySelectChildren?: boolean;
    shouldDisplayConfirmationFooter?: boolean;
    selectLabelProps?: SelectLabelProps;
    renderCustomOptionText?: CustomOptionRenderer<OptionType>;
}

export const selectDefaults: SelectProps = {
    options: [],
    label: '',
    size: 'md',
    showSearch: false,
    isDisabled: false,
    isReadOnly: false,
    isRequired: false,
    isMultiSelect: false,
    width: 255,
    height: 425,
    shouldDisplayConfirmationFooter: false,
};

export const NestedSelect = <OptionType extends NestedSelectOption = NestedSelectOption>({
    options = [],
    label = selectDefaults.label,
    initialValues = [],
    onUpdate,
    loadData,
    onSearch,
    showSearch = selectDefaults.showSearch,
    isDisabled = selectDefaults.isDisabled,
    isReadOnly = selectDefaults.isReadOnly,
    isRequired = selectDefaults.isRequired,
    isMultiSelect = selectDefaults.isMultiSelect,
    size = selectDefaults.size,
    areParentsSelectable = true,
    placeholder,
    searchPlaceholder,
    height = selectDefaults.height,
    isLoadingParentChildList = false,
    showClear = false,
    shouldAlwaysSyncParentValues = false,
    hideParentCheckbox = false,
    implicitlySelectChildren = true,
    shouldDisplayConfirmationFooter = selectDefaults.shouldDisplayConfirmationFooter,
    selectLabelProps,
    renderCustomOptionText,
    ...props
}: SelectProps<OptionType>) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [selectedOptions, setSelectedOptions] = useState<OptionType[]>(initialValues);
    const [stagedOptions, setStagedOptions] = useState<OptionType[]>(initialValues);
    const selectRef = useRef<HTMLDivElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (initialValues && shouldAlwaysSyncParentValues) {
            // Check if selectedOptions and initialValues are different
            const areDifferent = JSON.stringify(selectedOptions) !== JSON.stringify(initialValues);

            if (initialValues && areDifferent) {
                setSelectedOptions(initialValues);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialValues]);

    const handleDocumentClick = useCallback((e: MouseEvent) => {
        const clickedOutsideOfSelect = selectRef.current && !selectRef.current.contains(e.target as Node);
        const clickedOutsideOfDropdown = dropdownRef.current && !dropdownRef.current.contains(e.target as Node);

        if (clickedOutsideOfSelect && clickedOutsideOfDropdown) {
            setIsOpen(false);
        }
    }, []);

    useEffect(() => {
        document.addEventListener('click', handleDocumentClick);
        return () => {
            document.removeEventListener('click', handleDocumentClick);
        };
    }, [handleDocumentClick]);

    const handleSelectClick = useCallback(() => {
        if (!isDisabled && !isReadOnly) {
            setIsOpen((prev) => !prev);
        }
    }, [isDisabled, isReadOnly]);

    const handleSearch = useCallback(
        (query: string) => {
            setSearchQuery(query);
            onSearch?.(query);
        },
        [onSearch],
    );

    const filteredOptions = useMemo(() => {
        return filterNestedSelectOptions(options, searchQuery);
    }, [options, searchQuery]);

    // Instead of calling the update function individually whenever selectedOptions changes,
    // we use the useEffect hook to trigger the onUpdate function automatically when selectedOptions is updated.
    useEffect(() => {
        if (onUpdate) {
            onUpdate(selectedOptions);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedOptions]);

    // Sync staged and selected options automaticly when shouldDisplayConfirmationFooter disabled
    useEffect(() => {
        if (!shouldDisplayConfirmationFooter) setSelectedOptions(stagedOptions);
    }, [shouldDisplayConfirmationFooter, stagedOptions]);

    const onClickUpdateButton = useCallback(() => {
        setSelectedOptions(stagedOptions); // update selected options
        setIsOpen(false);
        handleSearch('');
    }, [stagedOptions, handleSearch]);

    const onClickCancelButton = useCallback(() => {
        setStagedOptions(selectedOptions); // reset staged options
        setIsOpen(false);
        handleSearch('');
    }, [selectedOptions, handleSearch]);

    const handleOptionChange = useCallback(
        (option: OptionType) => {
            let newStagedOptions: OptionType[];
            if (stagedOptions.find((o) => o.value === option.value)) {
                newStagedOptions = stagedOptions.filter((o) => o.value !== option.value);
            } else {
                newStagedOptions = [...stagedOptions, option];
            }
            setStagedOptions(newStagedOptions);
            if (!isMultiSelect) {
                setIsOpen(false);
            }
        },
        [stagedOptions, isMultiSelect],
    );

    const addOptions = useCallback(
        (optionsToAdd: OptionType[]) => {
            const existingValues = new Set(stagedOptions.map((option) => option.value));
            const filteredOptionsToAdd = optionsToAdd.filter((option) => !existingValues.has(option.value));
            if (filteredOptionsToAdd.length) {
                const newStagedOptions = [...stagedOptions, ...filteredOptionsToAdd];
                setStagedOptions(newStagedOptions);
            }
        },
        [stagedOptions],
    );

    const removeOptions = useCallback(
        (optionsToRemove: OptionType[], syncWithSelectedOptions?: boolean) => {
            const newValues = stagedOptions.filter(
                (selectedOption) => !optionsToRemove.find((o) => o.value === selectedOption.value),
            );
            setStagedOptions(newValues);
            if (syncWithSelectedOptions) setSelectedOptions(newValues);
        },
        [stagedOptions],
    );

    const handleClearSelection = useCallback(() => {
        setStagedOptions([]);
        setSelectedOptions([]);
        setIsOpen(false);
        if (onUpdate) {
            onUpdate([]);
        }
    }, [onUpdate]);

    const onDropdownOpenChange = useCallback(
        (open: boolean) => {
            setIsOpen(open);

            // reset staged options on dropdown's closing when shouldDisplayConfirmationFooter enabled
            if (shouldDisplayConfirmationFooter && !open) {
                setStagedOptions(selectedOptions);
            }
        },
        [selectedOptions, shouldDisplayConfirmationFooter],
    );

    useEffect(() => {
        onDropdownOpenChange(isOpen);
    }, [isOpen, onDropdownOpenChange]);

    // generate map for options to quickly fetch children
    const parentValueToOptions: { [parentValue: string]: OptionType[] } = {};
    filteredOptions.forEach((o) => {
        const parentValue = o.parentValue || NO_PARENT_VALUE;
        parentValueToOptions[parentValue] = parentValueToOptions[parentValue]
            ? [...parentValueToOptions[parentValue], o]
            : [o];
    });

    const rootOptions = parentValueToOptions[NO_PARENT_VALUE] || [];

    return (
        <Container ref={selectRef} size={size || 'md'} width={props.width || 255}>
            {label && <SelectLabel onClick={handleSelectClick}>{label}</SelectLabel>}
            <Dropdown
                open={isOpen}
                disabled={isDisabled}
                placement="bottomRight"
                dropdownRender={() => (
                    <DropdownContainer ref={dropdownRef} style={{ maxHeight: height, overflow: 'auto' }}>
                        {showSearch && (
                            <DropdownSearchBar
                                placeholder={searchPlaceholder}
                                value={searchQuery}
                                onChange={(value) => handleSearch(value)}
                                size={size}
                            />
                        )}
                        <OptionList>
                            {rootOptions.map((option) => {
                                const isParentOptionLabelExpanded = stagedOptions.find(
                                    (opt) => opt.parentValue === option.value,
                                );
                                return (
                                    <NestedOption
                                        key={option.value}
                                        selectedOptions={stagedOptions}
                                        option={option}
                                        parentValueToOptions={parentValueToOptions}
                                        handleOptionChange={handleOptionChange}
                                        addOptions={addOptions}
                                        removeOptions={removeOptions}
                                        loadData={loadData}
                                        isMultiSelect={isMultiSelect}
                                        setSelectedOptions={setStagedOptions}
                                        areParentsSelectable={areParentsSelectable}
                                        isLoadingParentChildList={isLoadingParentChildList}
                                        hideParentCheckbox={hideParentCheckbox}
                                        isParentOptionLabelExpanded={!!isParentOptionLabelExpanded}
                                        implicitlySelectChildren={implicitlySelectChildren}
                                        renderCustomOptionText={renderCustomOptionText}
                                    />
                                );
                            })}
                        </OptionList>
                        {shouldDisplayConfirmationFooter && (
                            <DropdownFooterActions onUpdate={onClickUpdateButton} onCancel={onClickCancelButton} />
                        )}
                    </DropdownContainer>
                )}
            >
                <SelectBase
                    isDisabled={isDisabled}
                    isReadOnly={isReadOnly}
                    isRequired={isRequired}
                    isOpen={isOpen}
                    onClick={handleSelectClick}
                    fontSize={size}
                    data-testid="nested-options-dropdown-container"
                    width={props.width}
                    {...props}
                >
                    <SelectLabelRenderer
                        selectedValues={selectedOptions.map((o) => o.value)}
                        options={options}
                        placeholder={placeholder || 'Select an option'}
                        isMultiSelect={isMultiSelect}
                        removeOption={(option) => removeOptions([option], true)}
                        {...(selectLabelProps || {})}
                    />
                    <SelectActionButtons
                        selectedOptions={selectedOptions}
                        isOpen={isOpen}
                        isDisabled={!!isDisabled}
                        isReadOnly={!!isReadOnly}
                        handleClearSelection={handleClearSelection}
                        fontSize={size}
                        showClear={showClear}
                    />
                </SelectBase>
            </Dropdown>
        </Container>
    );
};
