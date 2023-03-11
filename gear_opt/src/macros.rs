macro_rules! enumerated_struct {
    (
    $(#[$struct_attrs:meta])*
    pub struct $Struct:ident $(< $A:ident >)? {
        enum $Enum:ident;
        field type $FTy:ty;
        fields {
            $(pub $field:ident, $Variant:ident;)*
        }
        fn map$(<$B:ident>)?, FnMut($MapSrcTy:ty) -> $MapDestTy:ty;
    }) => {
        $(#[$struct_attrs])*
        pub struct $Struct<$($A,)?> {
            $( pub $field: $FTy, )*
        }

        #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
        pub enum $Enum {
            $( $Variant, )*
        }

        impl<$($A,)?> $Struct<$($A,)?> {
            pub fn from_fn<F: FnMut($Enum) -> $FTy>(mut f: F) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: f($Enum::$Variant), )*
                }
            }

            pub fn map<F, $($B,)?>(self, mut f: F) -> $Struct<$($B,)?>
            where F: FnMut($Enum, $MapSrcTy) -> $MapDestTy {
                $Struct {
                    $( $field: f($Enum::$Variant, self.$field), )*
                }
            }
        }

        impl<$($A,)?> From<$FTy> for $Struct<$($A,)?>
        where $FTy: Clone {
            fn from(x: $FTy) -> $Struct<$($A,)?> {
                Self::from_fn(|_| x.clone())
            }
        }

        impl $Enum {
            pub const COUNT: usize = 0
                $( + 1 + (0 * $Enum::$Variant as usize) )*
                ;

            #[allow(unused_variables)]
            pub fn from_index(i: usize) -> $Enum {
                let orig_i = i;
                $(
                    if i == 0 {
                        return $Enum::$Variant;
                    }
                    let i = i - 1;
                )*
                panic!(concat!("index {} out of bounds for ", stringify!($Enum)), orig_i)
            }

            pub fn iter() -> impl Iterator<Item = $Enum> {
                (0 .. $Enum::COUNT).map($Enum::from_index)
            }
        }

        impl<$($A,)?> core::ops::Add<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where
            $( $A: core::ops::Add<$A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn add(self, other: $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: self.$field + other.$field, )*
                }
            }
        }

        impl<'a, $($A,)?> core::ops::Add<&'a $Struct<$($A,)?>> for &'a $Struct<$($A,)?>
        where
            $( &'a $A: core::ops::Add<&'a $A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn add(self, other: &'a $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: &self.$field + &other.$field, )*
                }
            }
        }

        impl<$($A,)?> core::ops::AddAssign<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where $FTy: core::ops::AddAssign<$FTy> {
            fn add_assign(&mut self, other: $Struct<$($A,)?>) {
                $( self.$field += other.$field; )?
            }
        }

        impl<'a, $($A,)?> core::ops::AddAssign<&'a $Struct<$($A,)?>> for $Struct<$($A,)?>
        where $FTy: core::ops::AddAssign<&'a $FTy> {
            fn add_assign(&mut self, other: &'a $Struct<$($A,)?>) {
                $( self.$field += &other.$field; )?
            }
        }

        impl<$($A,)?> core::ops::AddAssign<$FTy> for $Struct<$($A,)?>
        where $FTy: core::ops::AddAssign<$FTy>, $FTy: Copy {
            fn add_assign(&mut self, other: $FTy) {
                $( self.$field += other; )?
            }
        }

        impl<'a, $($A,)?> core::ops::AddAssign<&'a $FTy> for $Struct<$($A,)?>
        where $FTy: core::ops::AddAssign<&'a $FTy> {
            fn add_assign(&mut self, other: &'a $FTy) {
                $( self.$field += other; )?
            }
        }

        impl<$($A,)?> core::ops::Sub<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where
            $( $A: core::ops::Sub<$A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn sub(self, other: $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: self.$field - other.$field, )*
                }
            }
        }

        impl<'a, $($A,)?> core::ops::Sub<&'a $Struct<$($A,)?>> for &'a $Struct<$($A,)?>
        where
            $( &'a $A: core::ops::Sub<&'a $A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn sub(self, other: &'a $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: &self.$field - &other.$field, )*
                }
            }
        }

        impl<$($A,)?> core::ops::Mul<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where
            $( $A: core::ops::Mul<$A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn mul(self, other: $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: self.$field * other.$field, )*
                }
            }
        }

        impl<'a, $($A,)?> core::ops::Mul<&'a $Struct<$($A,)?>> for &'a $Struct<$($A,)?>
        where
            $( &'a $A: core::ops::Mul<&'a $A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn mul(self, other: &'a $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: &self.$field * &other.$field, )*
                }
            }
        }

        impl<$($A,)?> core::ops::Index<$Enum> for $Struct<$($A,)?> {
            type Output = $FTy;
            fn index(&self, x: $Enum) -> &$FTy {
                match x {
                    $( $Enum::$Variant => &self.$field, )*
                }
            }
        }

        impl<$($A,)?> core::ops::IndexMut<$Enum> for $Struct<$($A,)?> {
            fn index_mut(&mut self, x: $Enum) -> &mut $FTy {
                match x {
                    $( $Enum::$Variant => &mut self.$field, )*
                }
            }
        }
    };
}
