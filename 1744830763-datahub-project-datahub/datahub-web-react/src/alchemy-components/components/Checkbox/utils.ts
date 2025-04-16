import theme, { colors } from '@components/theme';
import { SizeOptions } from '@src/alchemy-components/theme/config';

const checkboxBackgroundDefault = {
    default: colors.white,
    checked: theme.semanticTokens.colors.primary,
    error: theme.semanticTokens.colors.error,
    disabled: colors.gray[300],
};

const checkboxHoverColors = {
    default: colors.gray[100],
    error: colors.red[100],
    checked: colors.violet[100],
};

export function getCheckboxColor(checked: boolean, error: string, disabled: boolean, mode: 'background' | undefined) {
    if (disabled) return checkboxBackgroundDefault.disabled;
    if (error) return checkboxBackgroundDefault.error;
    if (checked) return checkboxBackgroundDefault.checked;
    return mode === 'background' ? checkboxBackgroundDefault.default : colors.gray[500];
}

export function getCheckboxHoverBackgroundColor(checked: boolean, error: string) {
    if (error) return checkboxHoverColors.error;
    if (checked) return checkboxHoverColors.checked;
    return checkboxHoverColors.default;
}

const sizeMap: Record<SizeOptions, string> = {
    xs: '16px',
    sm: '18px',
    md: '20px',
    lg: '22px',
    xl: '24px',
    inherit: '',
};

export function getCheckboxSize(size: SizeOptions) {
    return {
        height: sizeMap[size],
        width: sizeMap[size],
    };
}
