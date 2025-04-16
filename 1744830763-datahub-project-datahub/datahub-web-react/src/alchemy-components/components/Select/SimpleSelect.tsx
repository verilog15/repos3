import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Dropdown, Text } from '@components';
import { isEqual } from 'lodash';
import {
    ActionButtonsContainer,
    Container,
    DropdownContainer,
    LabelContainer,
    OptionContainer,
    OptionLabel,
    OptionList,
    SelectBase,
    SelectLabel,
    SelectLabelContainer,
    StyledCheckbox,
    StyledClearButton,
    StyledIcon,
} from './components';
import { ActionButtonsProps, SelectOption, SelectProps } from './types';
import SelectLabelRenderer from './private/SelectLabelRenderer/SelectLabelRenderer';
import DropdownSearchBar from './private/DropdownSearchBar';
import DropdownSelectAllOption from './private/DropdownSelectAllOption';

const SelectActionButtons = ({
    selectedValues,
    isOpen,
    isDisabled,
    isReadOnly,
    showClear,
    handleClearSelection,
}: ActionButtonsProps) => {
    return (
        <ActionButtonsContainer>
            {showClear && selectedValues.length > 0 && !isDisabled && !isReadOnly && (
                <StyledClearButton
                    icon={{ icon: 'Close', source: 'material', size: 'lg' }}
                    isCircle
                    onClick={handleClearSelection}
                />
            )}
            <StyledIcon icon="CaretDown" source="phosphor" rotate={isOpen ? '180' : '0'} size="md" color="gray" />
        </ActionButtonsContainer>
    );
};

export const selectDefaults: SelectProps = {
    options: [],
    label: '',
    size: 'md',
    showSearch: false,
    isDisabled: false,
    isReadOnly: false,
    isRequired: false,
    showClear: true,
    width: 255,
    isMultiSelect: false,
    placeholder: 'Select an option ',
    showSelectAll: false,
    selectAllLabel: 'Select All',
    showDescriptions: false,
    filterResultsByQuery: true,
    ignoreMaxHeight: false,
};

export const SimpleSelect = ({
    options = selectDefaults.options,
    label = selectDefaults.label,
    values,
    initialValues,
    onUpdate,
    showSearch = selectDefaults.showSearch,
    isDisabled = selectDefaults.isDisabled,
    isReadOnly = selectDefaults.isReadOnly,
    isRequired = selectDefaults.isRequired,
    showClear = selectDefaults.showClear,
    size = selectDefaults.size,
    icon,
    isMultiSelect = selectDefaults.isMultiSelect,
    placeholder = selectDefaults.placeholder,
    disabledValues = [],
    showSelectAll = selectDefaults.showSelectAll,
    selectAllLabel = selectDefaults.selectAllLabel,
    showDescriptions = selectDefaults.showDescriptions,
    optionListTestId,
    renderCustomOptionText,
    renderCustomSelectedValue,
    filterResultsByQuery = selectDefaults.filterResultsByQuery,
    onSearchChange,
    combinedSelectedAndSearchOptions,
    optionListStyle,
    optionSwitchable,
    selectLabelProps,
    position,
    applyHoverWidth,
    ignoreMaxHeight = selectDefaults.ignoreMaxHeight,
    ...props
}: SelectProps) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [selectedValues, setSelectedValues] = useState<string[]>(initialValues || values || []);
    const selectRef = useRef<HTMLDivElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const [areAllSelected, setAreAllSelected] = useState(false);

    useEffect(() => {
        if (values !== undefined && !isEqual(selectedValues, values)) {
            setSelectedValues(values);
        }
    }, [values, selectedValues]);

    useEffect(() => {
        setAreAllSelected(selectedValues.length === options.length);
    }, [options, selectedValues]);

    const filteredOptions = useMemo(
        () =>
            filterResultsByQuery
                ? options.filter((option) => option.label.toLowerCase().includes(searchQuery.toLowerCase()))
                : options,
        [options, searchQuery, filterResultsByQuery],
    );

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

    const handleOptionChange = useCallback(
        (option: SelectOption) => {
            const updatedValues = selectedValues.includes(option.value)
                ? selectedValues.filter((val) => val !== option.value)
                : [...selectedValues, option.value];

            setSelectedValues(isMultiSelect ? updatedValues : [option.value]);
            if (onUpdate) {
                onUpdate(isMultiSelect ? updatedValues : [option.value]);
            }
            if (!isMultiSelect) setIsOpen(false);
        },
        [onUpdate, isMultiSelect, selectedValues],
    );

    const handleClearSelection = useCallback(() => {
        setSelectedValues([]);
        setAreAllSelected(false);
        setIsOpen(false);
        if (onUpdate) {
            onUpdate([]);
        }
    }, [onUpdate]);

    const handleSelectAll = () => {
        if (areAllSelected) {
            setSelectedValues([]);
            onUpdate?.([]);
        } else {
            const allValues = options.map((option) => option.value);
            setSelectedValues(allValues);
            onUpdate?.(allValues);
        }
        setAreAllSelected(!areAllSelected);
    };

    const handleSearchChange = (value: string) => {
        onSearchChange?.(value);
        setSearchQuery(value);
    };

    const finalOptions = combinedSelectedAndSearchOptions?.length ? combinedSelectedAndSearchOptions : options;

    return (
        <Container
            ref={selectRef}
            size={size || 'md'}
            width={props.width || 255}
            $selectLabelVariant={selectLabelProps?.variant}
            isSelected={selectedValues.length > 0}
        >
            {label && <SelectLabel onClick={handleSelectClick}>{label}</SelectLabel>}
            <Dropdown
                open={isOpen}
                disabled={isDisabled}
                placement="bottomRight"
                dropdownRender={() => (
                    <DropdownContainer ref={dropdownRef} ignoreMaxHeight={ignoreMaxHeight}>
                        {showSearch && (
                            <DropdownSearchBar
                                placeholder="Search…"
                                value={searchQuery}
                                onChange={(value) => handleSearchChange(value)}
                                size={size}
                            />
                        )}
                        <OptionList style={optionListStyle} data-testid={optionListTestId}>
                            {showSelectAll && isMultiSelect && (
                                <DropdownSelectAllOption
                                    label={selectAllLabel}
                                    selected={areAllSelected}
                                    disabled={disabledValues.length === options.length}
                                    onClick={() => !(disabledValues.length === options.length) && handleSelectAll()}
                                />
                            )}
                            {filteredOptions.map((option) => (
                                <OptionLabel
                                    key={option.value}
                                    onClick={() => {
                                        if (!isMultiSelect) {
                                            if (optionSwitchable && selectedValues.includes(option.value)) {
                                                handleClearSelection();
                                            } else {
                                                handleOptionChange(option);
                                            }
                                        }
                                    }}
                                    isSelected={selectedValues.includes(option.value)}
                                    isMultiSelect={isMultiSelect}
                                    isDisabled={disabledValues?.includes(option.value)}
                                    applyHoverWidth={applyHoverWidth}
                                >
                                    {isMultiSelect ? (
                                        <LabelContainer>
                                            {renderCustomOptionText ? (
                                                renderCustomOptionText(option)
                                            ) : (
                                                <span>{option.label}</span>
                                            )}
                                            <StyledCheckbox
                                                onClick={() => handleOptionChange(option)}
                                                checked={selectedValues.includes(option.value)}
                                                disabled={disabledValues?.includes(option.value)}
                                            />
                                        </LabelContainer>
                                    ) : (
                                        <OptionContainer>
                                            {renderCustomOptionText ? (
                                                renderCustomOptionText(option)
                                            ) : (
                                                <ActionButtonsContainer>
                                                    {option.icon}
                                                    <Text
                                                        weight="semiBold"
                                                        size="md"
                                                        color={
                                                            selectedValues.includes(option.value) ? 'violet' : 'gray'
                                                        }
                                                    >
                                                        {option.label}
                                                    </Text>
                                                </ActionButtonsContainer>
                                            )}

                                            {!!option.description && (
                                                <Text color="gray" weight="normal" size="sm">
                                                    {option.description}
                                                </Text>
                                            )}
                                        </OptionContainer>
                                    )}
                                </OptionLabel>
                            ))}
                        </OptionList>
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
                    {...props}
                    position={position}
                >
                    <SelectLabelContainer>
                        {icon && <StyledIcon icon={icon} size="lg" />}
                        <SelectLabelRenderer
                            selectedValues={selectedValues}
                            options={finalOptions}
                            placeholder={placeholder || 'Select an option'}
                            isMultiSelect={isMultiSelect}
                            removeOption={handleOptionChange}
                            disabledValues={disabledValues}
                            showDescriptions={showDescriptions}
                            renderCustomSelectedValue={renderCustomSelectedValue}
                            {...(selectLabelProps || {})}
                        />
                    </SelectLabelContainer>
                    <SelectActionButtons
                        selectedValues={selectedValues}
                        isOpen={isOpen}
                        isDisabled={!!isDisabled}
                        isReadOnly={!!isReadOnly}
                        handleClearSelection={handleClearSelection}
                        showClear={!!showClear}
                    />
                </SelectBase>
            </Dropdown>
        </Container>
    );
};
