import React, { forwardRef, createElement, SVGProps } from 'react';

interface LogoProps extends SVGProps<SVGSVGElement> {
  size?: number;
  className?: string;
}

const defaultAttributes = {
  fill: 'none',
  xmlns: 'http://www.w3.org/2000/svg',
};

const mergeClasses = (...classes: string[]) => classes.filter(Boolean).join(' ');

const Logo = forwardRef<SVGSVGElement, LogoProps>(
  (
    {
      size = 410,
      className = '',
      ...rest
    },
    ref
  ) => {
    const baseSize = 410;
    const scale = size / baseSize;
    const iconNode = [
      { tag: 'circle', props: { cx: 205, cy: 205, r: 118, stroke: '#B1B1B1', strokeWidth: 64, fill: 'transparent' } },
      { tag: 'circle', props: { cx: 205, cy: 205, r: 58, fill: '#D9D9D9', stroke: '#D9D9D9', strokeWidth: 24 } },
      { tag: 'circle', props: { cx: 205, cy: 205, r: 185, stroke: '#898989', strokeWidth: 40, fill: 'transparent' } },
      // { tag: 'circle', props: { cx: 205, cy: 205, r: 118, stroke: '#B0B0B0', strokeWidth: 64, fill: 'transparent' } },
      // { tag: 'circle', props: { cx: 205, cy: 205, r: 58, fill: '#FF7F50', stroke: '#D9D9D9', strokeWidth: 24 } },
      // { tag: 'circle', props: { cx: 205, cy: 205, r: 185, stroke: '#F5F5F5', strokeWidth: 40, fill: 'transparent' } },
    ];

    return createElement(
      'svg',
      {
        ref,
        ...defaultAttributes,
        width: size,
        height: size,
        className: mergeClasses('logo', className),
        viewBox: `0 0 ${baseSize} ${baseSize}`,
        ...rest,
      },
      iconNode.map(({ tag, props }) => createElement(tag, { ...props, key: props.cx + props.cy + props.r, transform: `scale(${scale})` })),
    );
  },
);

export default Logo;