# React + TypeScript + Vite

이 템플릿은 Vite 환경에서 React를 HMR 및 몇 가지 ESLint 규칙과 함께 사용할 수 있도록 최소한의 설정을 제공합니다.

현재 두 가지 공식 플러그인을 사용할 수 있습니다:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) — Fast Refresh에 [Babel](https://babeljs.io/)을 사용
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) — Fast Refresh에 [SWC](https://swc.rs/)를 사용

## ESLint 설정 확장하기

프로덕션용 애플리케이션을 개발 중이라면, 타입 인식(type-aware) 린트 규칙을 활성화하도록 설정을 업데이트하는 것을 권장합니다.

- 최상위 `parserOptions` 속성을 다음과 같이 구성하세요:

```js
export default tseslint.config({
  languageOptions: {
    // 기타 옵션...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

- `tseslint.configs.recommended`를 `tseslint.configs.recommendedTypeChecked` 또는 `tseslint.configs.strictTypeChecked`로 교체하세요
- 선택적으로 `...tseslint.configs.stylisticTypeChecked`를 추가할 수 있습니다
- [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react)를 설치하고 설정을 업데이트하세요:

```js
// eslint.config.js
import react from 'eslint-plugin-react'

export default tseslint.config({
  // React 버전 설정
  settings: { react: { version: '18.3' } },
  plugins: {
    // React 플러그인 추가
    react,
  },
  rules: {
    // 기타 규칙...
    // 권장 규칙 활성화
    ...react.configs.recommended.rules,
    ...react.configs['jsx-runtime'].rules,
  },
})
```
